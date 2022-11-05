from __future__ import unicode_literals

import re

from functools import wraps

from telegram.ext import Updater, Filters, CommandHandler, MessageHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from i18n.translator import t

from slateboy.helpers import extractIDs


# just bunch of wrappers to avoid repeating code


def preCommand(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # restore the arguments
        self = args[0]
        update = args[1]
        context = args[2]

        # get the user_id
        chat_id, user_id = extractIDs(update)

        # pre-command callback
        self.personality.atCommand(context, user_id)

        # proceed
        return func(*args, **kwargs)
    return wrapper

def checkWallet(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # restore the arguments
        self = args[0]
        update = args[1]
        context = args[2]

        # get the user_id
        chat_id, user_id = extractIDs(update)

        # check if wallet is operational
        is_wallet_ready, reason = self.wallet.isReady()
        if not is_wallet_ready:
            return update.context.bot.send_message(
                chat_id=chat_id, text=reason)
        return func(*args, **kwargs)
    return wrapper


def checkEULA(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # restore the arguments
        self = args[0]
        update = args[1]
        context = args[2]

        # get the user_id
        chat_id, user_id = extractIDs(update)

        # check if the personality wishes this user to see the EULA
        needs_to_see, EULA, EULA_verion = self.personality.shouldSeeEULA(
            update, context)
        if not needs_to_see:
            return func(*args, **kwargs)

        button_msg_approve = t('slateboy.eula_approve')
        button_msg_deny = t('slateboy.eula_deny')
        callback_data_approve = 'eula-approve-' + EULA_verion
        callback_data_deny = 'eula-deny-' + EULA_verion
        reply_text = t('slateboy.msg_eula_info')

        context.bot.send_message(chat_id=user_id, text=reply_text)
        keyboard = [
            [InlineKeyboardButton(
                button_msg_approve, callback_data=callback_data_approve)],
            [InlineKeyboardButton(
                button_msg_deny, callback_data=callback_data_deny)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        return context.bot.send_message(
            chat_id=user_id, text=EULA, reply_markup=reply_markup)
    return wrapper


class checkShouldIgnore:
    def __init__(self, msg_reason_unknown):
        self.msg_reason_unknown = msg_reason_unknown

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # restore the arguments
            otherself = args[0]
            update = args[1]
            context = args[2]

            chat_id, user_id = extractIDs(update)

            # check if personality wishes to reject this flow
            ignore, reason = otherself.personality.shouldIgnore(update, context)
            if ignore:
                if reason is not None:
                    return context.bot.send_message(
                        chat_id=chat_id, text=reason)
                # unknown reason but still ordered to ignore
                reply_text = t(self.msg_reason_unknown)
                return context.bot.send_message(
                    chat_id=chat_id, text=reply_text)

            # looks like the personality wishes to continue
            return func(*args, **kwargs)
        return wrapper


class parseRequestedAmountArgument:
    def __init__(self, msg_missing, msg_invalid,
                 is_mandatory=False, allowed_max=False):
        self.is_mandatory = is_mandatory
        self.msg_missing = msg_missing
        self.msg_invalid = msg_invalid
        self.allowed_max = allowed_max

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # restore the arguments
            otherself = args[0]
            update = args[1]
            context = args[2]

            # get the user_id
            chat_id, user_id = extractIDs(update)

            # check if there is amount specified
            if len(context.args) == 0 and self.is_mandatory:
                reply_text = t(self.msg_missing)
                return context.bot.send_message(
                    chat_id=chat_id, text=reply_text)

            # validate the requested amount
            requested_amount = None
            try:
                requested_amount = float(context.args[0])
            except ValueError:
                if self.allowed_max and context.args[0] == 'max':
                    requested_amount = 'max'
                elif self.is_mandatory:
                    reply_text = t(self.msg_invalid).format(
                        context.args[0])
                    return context.bot.send_message(
                        chat_id=chat_id, text=reply_text)

            # either valid either ignored
            kwargs['requested_amount'] = requested_amount
            return func(*args, **kwargs)
        return wrapper


# legit SlateBoy class!

class SlateBoy:
    def __init__(self, name, api_key, personality, wallet_provider, namespace='slateboy', config={}, bot=None):
        self.bot = bot
        self.name = name
        self.api_key = api_key
        self.namespace = namespace
        self.wallet = wallet_provider

        # configuration
        self.config = config

        # register the personality instance
        self.personality = personality


    def initiate(self):
        # relevant configs
        frequency_job_txs = self.config.get('frequency_job_txs', 600)
        first_job_txs = self.config.get('first_job_txs', 60)

        frequency_wallet_sync = self.config.get('frequency_wallet_sync', 600)
        first_wallet_sync = self.config.get('first_wallet_sync', 5)

        # check if personality requested to update standard command names
        names = self.personality.renameStandardCommands()

        # command callbacks
        if self.bot is not None:
            self.updater = Updater(bot=self.bot)
        else:
            self.updater = Updater(self.api_key, use_context=True)

        # register standard commands
        self.updater.dispatcher.add_handler(
            CommandHandler(names.get('withdraw', 'withdraw'),
                           self.handlerRequestWithdraw))
        self.updater.dispatcher.add_handler(
            CommandHandler(names.get('deposit', 'deposit'),
                           self.handlerRequestDeposit))
        self.updater.dispatcher.add_handler(
            CommandHandler(names.get('balance', 'balance'),
                           self.handlerBalance))

        # register custom commands
        custom_commands = self.personality.registerCustomCommands()
        for command, function in custom_commands:
            self.updater.dispatcher.add_handler(
                CommandHandler(command, function))

        # regular message for handling slatepacks and other logic
        self.updater.dispatcher.add_handler(
            MessageHandler(Filters.text, self.genericTextHandler))

        # transaction status update job for deposits and withdrawals
        self.updater.job_queue.run_repeating(
            self.jobTXs, interval=frequency_job_txs,
            first=first_job_txs)

        # wallet refresh job for keeping it in sync
        self.updater.job_queue.run_repeating(
            self.jobWalletSync, interval=frequency_wallet_sync,
            first=first_wallet_sync)

        # register custom jobs requested by the personality
        custom_jobs = self.personality.registerCustomJobs()
        for fist_interval, frequency, function in custom_jobs:
            self.updater.job_queue.run_repeating(
                function, interval=frequency,
                first=first_interval)

        # callback query for button presses
        self.updater.dispatcher.add_handler(
            CallbackQueryHandler(self.callbackQueryHandler))

        self.updater.job_queue.run_once(self.personality.atStart, when=0)

    def run(self, idle=True):
        self.updater.start_polling()
        if idle:
            self.updater.idle()

    def stop(self):
        self.updater.stop()

    @preCommand
    @checkShouldIgnore('slateboy.msg_callback_query_ignored_unknown')
    def callbackQueryHandler(self, update, context):
        # get the user_id
        print('callbackQueryHandler')
        chat_id, user_id = extractIDs(update)

        # extract the query
        query = update.callback_query
        query.answer()

        # check if user approved the EULA
        if query.data.startswith('eula-approve-'):
            print('approve')
            EULA_version = query.data.split('eula-approve-')[1]
            reply_markup = self.personality.approvedEULA(
                update, context, EULA_version)
            query.edit_message_reply_markup(reply_markup=None)
            return False

        # check if user denied the EULA
        if query.data.startswith('eula-deny-'):
            print('reject')
            EULA_version = query.data.split('eula-deny-')[1]
            reply_markup = self.personality.deniedEULA(
                update, context, EULA_version)
            query.edit_message_reply_markup(reply_markup=None)
            return False

        # some custom logic imposed by the personality, let it handle
        reply_markup = self.personality.buttonPressed(update, context, query.data)
        query.edit_message_reply_markup(reply_markup=None)
        return False

    @checkWallet
    @preCommand
    @checkShouldIgnore('slateboy.msg_withdraw_ignored_unknown')
    @parseRequestedAmountArgument(
        'slateboy.msg_withdraw_missing_amount',
        'slateboy.msg_withdraw_invalid_amount',
        is_mandatory=False, allowed_max=True)
    def handlerRequestWithdraw(self, update, context, requested_amount=None):
        # get the user_id
        chat_id, user_id = extractIDs(update)

        # consult the personality
        success, reason, result, approved_amount = self.personality.canWithdraw(
            update, context, requested_amount, maximum=is_maximum_request)

        # process the personality's response
        shall_continue = self.validateFinancialOperation(
            update, context, success, reason, result,
            requested_amount, approved_amount,
            'slateboy.msg_withdraw_rejected_known',
            'slateboy.msg_withdraw_rejected_unknown')
        if not shall_continue:
            return shall_continue

        # if reached here, it means it is approved
        # begin the SRS flow
        success, reason, slatepack, tx_id = self.wallet.send(approved_amount)

        # check if for some reason it has failed,
        # example reason could be all the outputs are locked at the moment
        if not success:
            update.context.bot.send_message(
                chat_id=chat_id, text=reason)
            shall_continue = False
            return shall_continue

        # let the personality assign this tx_id
        success, reason = self.personality.assignWithdrawTx(
            update, context, approved_amount, tx_id)

        # did it not work for some reason?
        if not success:
            # release the locked outputs by cancelling the tx
            self.wallet.releaseLock(tx_id)

            # inform the user of the failure
            update.context.bot.send_message(
                chat_id=chat_id, text=reason)
            shall_continue = False
            return shall_continue

        # complete the RSR flow initialization
        shall_continue = self.completeFinancialOperation(
            update, context, slatepack,
            self.personality.customWithdrawInstructions,
            self.personality.customWithdrawSlatepackFormatting,
            self.personality.customWithdrawFinalMessage,
            'slateboy.msg_withdraw_instructions',
            'slateboy.msg_withdraw_slatepack_formatting')
        return shall_continue


    @checkWallet
    @preCommand
    @checkEULA
    @checkShouldIgnore('slateboy.msg_deposit_ignored_unknown')
    @parseRequestedAmountArgument(
        'slateboy.msg_deposit_missing_amount',
        'slateboy.msg_deposit_invalid_amount',
        allowed_max=False, is_mandatory=True)
    def handlerRequestDeposit(self, update, context, requested_amount=None):
        # get the user_id
        chat_id, user_id = extractIDs(update)

        # consult the personality if this deposit is approved
        success, reason, result, approved_amount = self.personality.canDeposit(
            update, context, requested_amount)

        # process the personality's response
        shall_continue = self.validateFinancialOperation(
            update, context, success, reason, result,
            requested_amount, approved_amount,
            'slateboy.msg_deposit_rejected_known',
            'slateboy.msg_deposit_rejected_unknown')
        if not shall_continue:
            return shall_continue

        # if reached here, it means it is approved
        # begin the RSR flow
        success, reason, slatepack, tx_id = self.wallet.invoice(approved_amount)

        # check if for some reason it has failed
        if not success:
            context.bot.send_message(
                chat_id=chat_id, text=reason)
            shall_continue = False
            return shall_continue

        # let the personality assign this tx_id
        success, reason, send_instructions, msg = self.personality.assignDepositTx(
            update, context, approved_amount, tx_id)

        # did it not work for some reason?
        if not success:
            # release the locked outputs
            self.wallet.releaseLock(tx_id)

            # inform the user of the failure
            context.bot.send_message(
                chat_id=chat_id, text=reason)
            shall_continue = False
            return shall_continue

        # complete the RSR flow initialization
        shall_continue = self.completeFinancialOperation(
            update, context, slatepack,
            self.personality.customDepositInstructions,
            self.personality.customDepositSlatepackFormatting,
            self.personality.customDepositFinalMessage,
            'slateboy.msg_deposit_instructions',
            'slateboy.msg_deposit_slatepack_formatting')
        return shall_continue


    @preCommand
    @checkShouldIgnore('slateboy.msg_balance_ignored_unknown')
    def handlerBalance(self, update, context):
        # get the user_id
        chat_id, user_id = extractIDs(update)

        # consult the personality to get the balance
        success, reason, balance = self.personality.getBalance(
            update, context)

        # is something wrong?
        if not success:
            update.context.bot.send_message(
                chat_id=chat_id, text=reason)
            shall_continue = False
            return shall_continue

        # personality can provide already formatted message ready
        # for the user
        if isinstance(balance, str):
            context.bot.send_message(
                chat_id=chat_id, text=balance)
            shall_continue = False
            return shall_continue

        # personality can also provide just separate balances
        # as a tuple and let the slateboy format it
        spendable, awaiting_confirmation, awaiting_finalization, locked = balance
        reply_text = t('slateboy.msg_balance').format(**{
            'spendable': str(spendable),
            'awaiting_confirmation': str(awaiting_confirmation),
            'awaiting_finalization': str(awaiting_finalization),
            'locked': str(locked)
        })
        context.bot.send_message(
            chat_id=chat_id, text=reply_text)
        shall_continue = False
        return shall_continue


    @checkShouldIgnore('slateboy.msg_generic_ignored_unknown')
    def genericTextHandler(self, update, context):
        # get the user_id and the message_id
        chat_id, user_id = extractIDs(update)
        message_id = update.message.message_id

        # does it contain a slatepack?
        contains_slatepack, slatepack = self.containsSlatepack(update.message.text)

        # let the personality process the message
        shall_continue, reason = self.personality.incomingText(
            update, context, contains_slatepack)
        if not shall_continue:
            if reason is not None:
                context.bot.send_message(
                    chat_id=chat_id, text=reason)
            return shall_continue

        # is it a group message?
        is_group_message = update.message.chat.type != 'private'
        if is_group_message:
            shall_continue, reason = self.personality.incomingTextGroup(
                update, context, contains_slatepack)
            if not shall_continue:
                if reason is not None:
                    context.bot.send_message(
                        chat_id=chat_id, text=reason)
                return shall_continue

        # is it a DM?
        is_direct_message = update.message.chat.type == 'private'
        if is_direct_message:
            shall_continue, reason = self.personality.incomingTextDM(
                update, context, contains_slatepack)
            if not shall_continue:
                if reason is not None:
                    context.bot.send_message(
                        chat_id=chat_id, text=reason)
                return shall_continue

        # for direct messages with a slatepack we proceed with the flow
        if (not is_direct_message) and contains_slatepack:
            custom_public_slatepack_warning = self.personality.customPublicSlatepackWarning()
            if custom_public_slatepack_warning is not None:
                context.bot.send_message(
                    reply_to_message_id=message_id,
                    chat_id=chat_id,
                    text=custom_public_slatepack_warning)
            shall_continue = False
            return shall_continue

        # looks like it is direct message with a slatepack
        slate = self.wallet.decodeSlatepack(slatepack)
        tx_id = slate.get('id', -1)
        sta = slate.get('sta', -1)

        # S1 - attempts of deposit
        if sta == 'S1':
            # the following processing function will execute
            # the logic along with the personality to ensure
            # such a deposit is approved
            return self.processS1Slatepack(update, context, slate, tx_id)

        # S2 - withdrawal flow, user responded with a slatepack
        if sta == 'S2':
            # the following processing function will execute
            # the logic along with the personality to ensure
            # such a withdrawal may continue
            return self.processS2Slatepack(update, context, slate, tx_id)

        # I1 - user sent us an invoice
        if sta == 'I1':
            # at this stage we have no logic for such a scenario,
            # inform the user we ignore it
            reply_text = t('slateboy.msg_ignoring_invoices')
            return context.bot.send_message(
                        chat_id=chat_id, text=reply_text,
                        reply_to_message_id=message_id)

        # I2 - user responded to our invoice
        if sta == 'I2':
            # complete the deposit using the invoice flow
            return self.processI2Slatepack(update, context, slate, tx_id)


    def jobTXs(self, context):
        pass

    def jobWalletSync(self, context):
        pass

    # wrappers

    @checkWallet
    @checkEULA
    def processS1Slatepack(self, update, context, slate, tx_id):
        # get the user_id and the message_id
        chat_id, user_id = extractIDs(update)

        # get the amount from the slatepack
        requested_amount = slate.get('amt', -1)
        if requested_amount == -1:
            reply_text = t('slateboy.msg_invalid_slatepack')
            context.bot.send_message(
                chat_id=user_id, text=reply_text)
            shall_continue = False
            return shall_continue

        # consult the personality if this deposit is approved
        success, reason, result, approved_amount = self.personality.canDeposit(
            update, context, requested_amount)

        # process the personality's response
        shall_continue = self.validateFinancialOperation(
            update, context, success, reason, result,
            requested_amount, approved_amount,
            'slateboy.msg_deposit_rejected_known',
            'slateboy.msg_deposit_rejected_unknown')
        if not shall_continue:
            return shall_continue

        # if reached here, it means it is approved
        # begin the SRS flow
        success, reason, slatepack, tx_id = self.wallet.receive(approved_amount) # TODO this should be slatepack!

        # check if for some reason it has failed
        if not success:
            context.bot.send_message(
                chat_id=chat_id, text=reason)
            shall_continue = False
            return shall_continue

        # looks like all is approved, let us run the receive
        # let the personality assign this tx_id
        success, reason, send_instructions, msg = self.personality.assignDepositTx(
                update, context, approved_amount, tx_id)

        # did it not work for some reason?
        if not success:
            # release the locked outputs
            self.wallet.releaseLock(tx_id)

            # inform the user of the failure
            context.bot.send_message(
                chat_id=chat_id, text=reason)
            shall_continue = False
            return shall_continue

        # complete the SRS flow instructions
        shall_continue = self.completeFinancialOperation(
            update, context, slatepack,
            self.personality.customSRSDepositInstructions,
            self.personality.customSRSDepositSlatepackFormatting,
            self.personality.customSRSDepositFinalMessage,
            'slateboy.msg_deposit_srs_instructions',
            'slateboy.msg_deposit_srs_slatepack_formatting')
        return shall_continue

    @checkWallet
    def processS2Slatepack(self, update, context, slatepack, tx_id):
        return self.processSlatepack(
            update, context, slatepack, tx_id,
            self.personality.shouldFinalizeWithdrawTx,
            self.personality.finalizeWithdrawTx,
            'slateboy.msg_i2_withdraw_rejected_unknown',
            'slateboy.msg_withdraw_finalized')


    @checkWallet
    def processI2Slatepack(update, context, slatepack, tx_id):
        return self.processSlatepack(
            update, context, slatepack, tx_id,
            self.personality.shouldFinalizeDepositTx,
            self.personality.finalizeDepositTx,
            'slateboy.msg_s2_deposit_rejected_unknown',
            'slateboy.msg_deposit_finalized')

    # some helpers

    def containsSlatepack(self, text):
        regex = 'BEGINSLATEPACK[\\s\\S]*\\sENDSLATEPACK'
        matches = re.search(regex, text, flags=re.DOTALL)
        contains_slatepack = False
        slatepack = None
        if matches is not None:
            contains_slatepack = True
            slatepack = matches.group(0).replace('\n', '')
        return contains_slatepack, slatepack

    def validateFinancialOperation(
            self,
            update,
            context,
            processing_success,
            reason_of_failure,
            allowed,
            requested_amount,
            approved_amount, reject_reason_known, reject_reason_unknown):
        # get the user_id and the message_id
        chat_id, user_id = extractIDs(update)

        # check if user has violated ny terms
        if not allowed and reason_of_failure is None and approved_amount is not None:
            reply_text = t(reject_reason_known).format(
                str(requested_amount), str(approved_amount))
            context.bot.send_message(
                chat_id=chat_id, text=reply_text)
            shall_continue = False
            return shall_continue

        # there might have been custom logic reason why the personality
        # has decided to reject this request
        if not allowed and reason_of_failure is not None:
            context.bot.send_message(
                chat_id=chat_id, text=reason_of_failure)
            shall_continue = False
            return shall_continue

        # rejected for unknown reasons
        if not allowed:
            reply_text = t(reject_reason_unknown)
            context.bot.send_message(
                chat_id=chat_id, text=reply_text)
            shall_continue = False
            return shall_continue

        shall_continue = True
        return shall_continue

    def completeFinancialOperation(
            self,
            update,
            context,
            slatepack,
            customInstructionsMethod,
            customSlatepackFormattingMethod,
            finalMessageMethod,
            standard_instructions, standard_slatepack_formatting):
        # get the user_id
        chat_id, user_id = extractIDs(update)

        # check if personality wants custom instruction send
        send_instructions, custom_instructions = customInstructionsMethod(update, context)
        if send_instructions:
            if custom_instructions is None:
                reply_text = t(standard_instructions)
                context.bot.send_message(
                    chat_id=chat_id, text=reply_text)
            else:
                context.bot.send_message(
                    chat_id=chat_id, text=custom_instructions)

        # send slatepack and or message from the personality
        custom_slatepack_formatting = customSlatepackFormattingMethod(update, context)
        if custom_slatepack_formatting is not None:
            reply_text = custom_slatepack_formatting.format(
                **{'slatepack': slatepack})
        else:
            reply_text = t(standard_slatepack_formatting).format(
                **{'slatepack': slatepack})
        context.bot.send_message(
            chat_id=user_id, text=reply_text)

        # check if personality wants something sent to the user
        final_message = finalMessageMethod(update, context)
        if final_message is not None:
            context.bot.send_message(
                chat_id=user_id, text=final_message)

        shall_continue = False
        return shall_continue

    def processSlatepack(
            self, update, context, slatepack, tx_id,
            shouldFinalizeQueryMethod,
            finalizedTxMethod,
            msg_slatepack_rejected,
            msg_slatepack_finalized):
        # get the user_id and the message_id
        chat_id, user_id = extractIDs(update)

        # check if personality wishes to finalize it
        should_finalize, reason = shouldFinalizeQueryMethod(update, context, tx_id)
        if not should_finalize:
            if reason is not None:
                context.bot.send_message(
                    chat_id=user_id, text=reason)
                shall_continue = False
                return shall_continue
            reply_text = t(msg_slatepack_rejected)
            context.bot.send_message(
                chat_id=user_id, text=reply_text)
            shall_continue = False
            return shall_continue

        # finalization approved
        success, reason, finalized_slatepack = self.wallet.finalize(slatepack)

        # did it not work for some reason?
        if not success:
            # inform the user of the failure
            context.bot.send_message(
                chat_id=user_id, text=reason)
            shall_continue = False
            return shall_continue

        # inform personality of successful finalization
        success, reason, msg = finalizedTxMethod(update, context, tx_id)

        # did it not work for some reason?
        if not success:
            # inform the user of the failure
            context.bot.send_message(
                chat_id=user_id, text=reason)
            shall_continue = False
            return shall_continue

        if msg is not None:
            context.bot.send_message(
                chat_id=user_id, text=msg)
            shall_continue = False
            return shall_continue

        reply_text = t(msg_slatepack_finalized)
        context.bot.send_message(
                chat_id=user_id, text=reply_text)
        shall_continue = False
        return shall_continue

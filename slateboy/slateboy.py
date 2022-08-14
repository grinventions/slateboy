from __future__ import unicode_literals

import re

from telegram.ext import Updater, CommandHandler, MessageHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from i18n.translator import t

# default context checkers and initiators
from slateboy.defaults import default_is_bank_balance_initiated
from slateboy.defaults import default_initiate_bank_balance

from slateboy.defaults import default_is_user_balance_initiated
from slateboy.defaults import default_initiate_user_balance

# default methods for handling operations
from slateboy.defaults import default_balance
from slateboy.defaults import default_callback_withdraw_lock
from slateboy.defaults import default_callback_deposit_lock
from slateboy.defaults import default_is_txid_known
from slateboy.defaults import default_callback_withdraw
from slateboy.defaults import default_callback_deposit

# default job handling
from slateboy.defaults import default_callback_job_txs
from slateboy.defaults import default_callback_job_accounting

# policy configuration values
from slateboy.values import UserBehavior, BotBehavior


class SlateBoy:
    def __init__(self, name, api_key, personality, config={}):
        self.name = name
        self.api_key = api_key
        self.namespace = namespace

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
        self.updater = Updater(self.api_key, use_context=True)
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
            self.jobTXs, interval=self.frequency_job_txs,
            first=first_job_txs)

        # wallet refresh job for keeping it in sync
        self.updater.job_queue.run_repeating(
            self.jobWalletSynce, interval=self.frequency_wallet_sync,
            first=first_wallet_sync)

        # register custom jobs requested by the personality
        custom_jobs = registerCustomJobs()
        for fist_interval, frequency, function in custom_jobs:
            self.updater.job_queue.run_repeating(
                function, interval=frequency,
                first=first_interval)


    def run(self):
        self.updater.start_polling()
        self.updater.idle()


    def handlerRequestWithdraw(self, update, context):
        # get the user_id
        chat_id = update.message.chat.id

        # check if wallet is operational
        is_wallet_ready, reason = self.isWalletReady()
        if not is_wallet_ready:
            return update.context.bot.send_message(
                chat_id=chat_id, text=reason)

        # check if personality wishes to reject this flow
        ignore, reason = self.personality.shouldIgnore(update, context)
        if ignore:
            if reason is not None:
                return update.context.bot.send_message(
                    chat_id=chat_id, text=reason)
            # unknown reason but still ordered to ignore
            reply_text = t('slateboy.msg_ignored_unknown')
            return update.context.bot.send_message(
                chat_id=chat_id, text=reason)

        # validate the request amount
        is_maximum_request = False
        requested_amount = None

        if len(context.args) == 0:
            is_maximum_request = True
        else:
            try:
                requested_amount = float(context.args[0])
            except ValueError:
                reply_text = t('slateboy.msg_withdraw_invalid_amount').format(
                    context.args[0])
                return update.context.bot.send_message(
                    chat_id=chat_id, text=reply_text)

        # consult the personality
        success, reason, result, approved_amount = self.personality.canWithdraw(
            update, context, requested_amount, maximum=is_maximum_request)

        # check if user has requested too much?
        if not result and reason is None and approved_amount is not None:
            reply_text = t('slateboy.msg_withdraw_balance_exceeded').format(
                str(requested_amount), str(approved_amount))
            return update.context.bot.send_message(
                chat_id=chat_id, text=reply_text)

        # there might have been custom logic reason why the personality
        # has decided to reject this request
        if not result and reason is not None:
            return update.context.bot.send_message(
                chat_id=chat_id, text=reason)

        # rejected for unknown reasons
        if not result:
            reply_text = t('slateboy.msg_withdraw_rejected_unknown')
            return update.context.bot.send_message(
                chat_id=chat_id, text=reply_text)

        # if reached here, it means it is approved
        # begin the SRS flow
        success, reason, slatepack, tx_id = self.walletSend(approved_amount)

        # check if for some reason it has failed,
        # example reason could be all the outputs are locked at the moment
        if not success:
            return update.context.bot.send_message(
                chat_id=chat_id, text=reason)

        # let the personality assign this tx_id
        success, reason, send_instructions, msg = self.personality.assignWithdrawTx(
            update, context, approved_amount, tx_id)

        # did it not work for some reason?
        if not success:
            # release the locked outputs
            self.walletReleaseLock(tx_id)

            # inform the user of the failure
            return update.context.bot.send_message(
                chat_id=chat_id, text=reason)

        # check if personality wants withdrawal instruction send
        if send_instructions:
            reply_text = t('slateboy.msg_withdraw_instructions')
            return update.context.bot.send_message(
                chat_id=chat_id, text=reply_text)

        # send slatepack and or message from the personality
        if '{slatepack}' in msg:
            replyt_text = msg.format(slatepack)
            return update.context.bot.send_message(
                chat_id=chat_id, text=reason)

        # personality did not specify how to format the slatepack
        # sending it separately
        update.context.bot.send_message(chat_id=chat_id, text=slatepack)

        # check if personality wants something sent to the user
        if msg is not None and msg != '':
            return update.context.bot.send_message(
                chat_id=chat_id, text=msg)


    def handlerRequestDeposit(self, update, context):
        # get the user_id
        chat_id = update.message.chat.id

        # check if wallet is operational
        is_wallet_ready, reason = self.isWalletReady()
        if not is_wallet_ready:
            return update.context.bot.send_message(
                chat_id=chat_id, text=reason)

        # check if the personality wishes this user to see the EULA
        needs_to_see, EULA, EULA_verion = self.personality.shouldSeeEULA(self, update, context)
        if needs_to_see:
            button_msg_approve = t('slateboy.eula_approve')
            button_msg_deny = t('slateboy.eula_deny')
            callback_data_approve = 'eula-approve-' + EULA_verion
            callback_data_deny = 'eula-deny-' + EULA_verion
            reply_text = t('slateboy.msg_eula_info')
            update.context.bot.send_message(chat_id=chat_id, text=reply_text)
            keyboard = [
                [InlineKeyboardButton(
                    button_msg_approve, callback_data=callback_data_approve)],
                [InlineKeyboardButton(
                    button_msg_deny, callback_data=callback_data_deny)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            return update.context.bot.send_message(
                chat_id=chat_id, text=EULA, reply_markup=reply_markup)

        # check if there is amount specified
        if len(context.args) == 0:
            # inform the user that has to specify the amount to use /deposit
            # command, it is possible to deposit without specifying the amount
            # by simply sending an SRS slatepack
            reply_text = t('slateboy.msg_deposit_missing_amount')
            return update.context.bot.send_message(chat_id=chat_id, text=reply_text)

        # validate the request amount
        requested_amount = None
        try:
            requested_amount = float(context.args[0])
        except ValueError:
            # inform the user the amount is invalid, but it is possible
            # to just send a slatepack
            reply_text = t('slateboy.msg_deposit_invalid_amount').format(
                    context.args[0])
            return update.context.bot.send_message(
                    chat_id=chat_id, text=reply_text)

        # consult the personality if this deposit is approved
        success, reason, result, approved_amount = self.personality.canDeposit(
            update, context, requested_amount)

        # there might have been custom logic reason why the personality
        # has decided to reject this request
        if not result and reason is not None:
            return update.context.bot.send_message(
                chat_id=chat_id, text=reason)

        # rejected for unknown reasons
        if not result:
            reply_text = t('slateboy.msg_deposit_rejected_unknown')
            return update.context.bot.send_message(
                chat_id=chat_id, text=reply_text)

        # if reached here, it means it is approved
        # begin the RSR flow
        success, reason, slatepack, tx_id = self.walletInvoice(approved_amount)

        # check if for some reason it has failed
        if not success:
            return update.context.bot.send_message(
                chat_id=chat_id, text=reason)

        # let the personality assign this tx_id
        success, reason, send_instructions, msg = self.personality.assignDepositTx(
            update, context, approved_amount, tx_id)

        # did it not work for some reason?
        if not success:
            # release the locked outputs
            self.walletReleaseLock(tx_id)

            # inform the user of the failure
            return update.context.bot.send_message(
                chat_id=chat_id, text=reason)

        # check if personality wants deposit instruction send
        if send_instructions:
            reply_text = t('slateboy.msg_deposit_instructions')
            return update.context.bot.send_message(
                chat_id=chat_id, text=reply_text)

        # send slatepack and or message from the personality
        if '{slatepack}' in msg:
            replyt_text = msg.format(slatepack)
            return update.context.bot.send_message(
                chat_id=chat_id, text=reason)

        # personality did not specify how to format the slatepack
        # sending it separately
        update.context.bot.send_message(chat_id=chat_id, text=slatepack)

        # check if personality wants something sent to the user
        if msg is not None and msg != '':
            return update.context.bot.send_message(
                chat_id=chat_id, text=msg)


    def handlerBalance(self, update, context):
        # get the user_id
        chat_id = update.message.chat.id

        # check if personality wishes to reject this flow
        ignore, reason = self.personality.shouldIgnore(update, context)
        if ignore:
            if reason is not None:
                return update.context.bot.send_message(
                    chat_id=chat_id, text=reason)
            # unknown reason but still ordered to ignore
            reply_text = t('slateboy.msg_ignored_unknown')
            return update.context.bot.send_message(
                chat_id=chat_id, text=reason)

        # consult the personality to get the balance
        success, reason, balance = self.personality.getBalance(
            update, context)

        # is something wrong?
        if not success:
            return update.context.bot.send_message(
                chat_id=chat_id, text=reason)

        # personality can provide already formatted message ready
        # for the user
        if isinstance(balance, str):
            return update.context.bot.send_message(
                chat_id=chat_id, text=balance)

        # personality can also provide just separate balances
        # as a tuple and let the slateboy format it
        spendable, awaiting_confirmation, awaiting_finalization, locked = balance
        reply_text = t('slateboy.msg_balance').format(
            str(spendable), str(awaiting_confirmation),
            str(awaiting_finalization), str(locked))
        return update.context.bot.send_message(
                chat_id=chat_id, text=reply_text)


    def genericTextHandler(self, update, context):
        chat_id = update.message.chat.id
        message_id = update.message.message_id

        # distinguish DMs from group messages
        if update.message.chat.type == 'private':
            # check if it is a slatepack
            regex = 'BEGINSLATEPACK[\\s\\S]*\\sENDSLATEPACK'
            matches = re.search(regex, update.message.text, flags=re.DOTALL)
            if matches is not None:
                slatepack = matches.group(0)

                # check the meaning of the slatepack
                slate = self.walletDecodeSlatepack(slatepack)
                txid = slate.get('id', -1)
                if not self.callback_is_txid_known(update, context, txid):
                    reply_text = t('slateboy.msg_unknown_slatepack')
                    return update.context.bot.send_message(
                        chat_id=chat_id, text=reply_text,
                        reply_to_message_id=message_id)

                sta = slate.get('sta', -1)
                # slatepack is known, is this srs flow?
                if sta == 'S1':
                    # this is a deposit attempt
                    # TODO run receive
                    # TODO return instructions and response slatepack
                    return None

                if sta == 'S2':
                    # this is response to withdrawal
                    # TODO run finalize
                    # TODO return instructions
                    return None

                if sta == 'I1':
                    # user sent us an invoice, we ignore
                    # TODO inform user we do not pay invoices
                    return None

                if sta == 'I2':
                    # user has responded to our invoice
                    # this is deposit
                    # TODO run finalize
                    # TODO return instructions
                    return None

                # TODO inform user of reception of an invalid status code
                return None


    def jobTXs(self, context):
        self.callback_job_txs(context, self.walletQueryConfirmed, self.config_job_txs)

    def jobWalletSynce(self, context):
        pass


    # GRIN wallet methods TODO

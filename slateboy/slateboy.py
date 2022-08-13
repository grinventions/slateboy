from __future__ import unicode_literals

import re

from telegram.ext import Updater, CommandHandler, MessageHandler
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

        # check if wallet is operations
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
        # perform the invoice flow
        success, reason, slatepack, tx_id = self.walletInvoice(approved_amount)

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
        # TODO


    def handlerBalance(self, update, context):
        # TODO


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

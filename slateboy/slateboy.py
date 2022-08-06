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
    def __init__(self, name, api_key, namespace,
                 # policy
                 policy_user_context_attempt_create=[UserBehavior.REQUEST_DEPOSIT],
                 policy_user_context_attempt_destroy=[UserBehavior.INACTIVITY],
                 # callbacks
                 callback_is_bank_balance_initiated=default_is_bank_balance_initiated,
                 callback_initiate_bank_balance=default_initiate_bank_balance,
                 callback_is_user_balance_initiated=default_is_user_balance_initiated,
                 callback_initiate_user_balance=default_initiate_user_balance,
                 callback_balance=default_balance,
                 callback_withdraw=default_callback_withdraw,
                 callback_withdraw_lock=default_callback_withdraw_lock,
                 callback_deposit=default_callback_deposit,
                 callback_is_txid_known=default_is_txid_known,
                 callback_job_txs=default_callback_job_txs,
                 callback_job_accounting=default_callback_job_accounting,
                 frequency_job_txs=600,
                 frequency_job_accounting=3600,
                 config_job_txs={},
                 config_job_accounting={}):
        self.name = name
        self.api_key = api_key
        self.namespace = namespace

        # set the policy
        self.policy_user_context_create = policy_user_context_create
        self.policy_user_context_attempt_destroy = policy_user_context_attempt_destroy

        # register callbacks
        self.callback_is_bank_balance_initiated = callback_is_bank_balance_initiated
        self.callback_initiate_bank_balance = callback_initiate_bank_balance

        self.callback_is_user_balance_initiated = callback_is_user_balance_initiated
        self.callback_initiate_user_balance = callback_initiate_user_balance

        self.callback_balance = callback_balance
        self.callback_withdraw = callback_withdraw
        self.callback_withdraw_lock = callback_withdraw_lock
        self.callback_deposit = callback_deposit
        self.callback_is_txid_known = callback_is_txid_known

        # register jobs
        self.callback_job_txs = callback_job_txs
        self.callback_job_accounting = callback_job_accounting

        # job parameters
        self.frequency_job_txs = frequency_job_txs
        self.frequency_job_accounting = frequency_job_accounting

        # configs
        self.config_job_txs = config_job_txs
        self.config_job_accounting = config_job_accounting


    def initiate(self):
        # command callbacks
        self.updater = Updater(self.api_key, use_context=True)
        self.updater.dispatcher.add_handler(
            CommandHandler('withdraw', self.handlerRequestWithdraw))
        self.updater.dispatcher.add_handler(
            CommandHandler('deposit', self.handlerRequestDeposit))
        self.updater.dispatcher.add_handler(
            CommandHandler('balance', self.handlerBalance))

        # regular message for handling slatepacks
        self.updater.dispatcher.add_handler(
            MessageHandler(Filters.text, self.genericTextHandler))

        # jobs
        self.updater.job_queue.run_repeating(
            self.jobTXs, interval=self.frequency_job_txs,
            first=frequency_job_txs)
        self.updater.job_queue.run_repeating(
            self.jobAccounting, interval=self.frequency_job_accounting,
            first=frequency_job_accounting)


    def run(self):
        self.updater.start_polling()
        self.updater.idle()


    def handlerRequestWithdraw(self, update, context):
        chat_id = update.message.chat.id

        # validate the request amount
        requested_amount = 'max'
        if len(context.args) == 0:
            reply_text = t('slateboy.msg_withdraw_missing_amount')
            return update.context.bot.send_message(chat_id=chat_id, text=reply_text)
        else:
            try:
                requested_amount = float(context.args[0])
            except ValueError:
                reply_text = t('slateboy.msg_withdraw_invalid_amount').format(
                    context.args[0])
                return update.context.bot.send_message(
                    chat_id=chat_id, text=reply_text)

        # check if user can withdraw
        approved, reason, maximum = self.callback_withdraw(
            self, update, context, requested_amount)

        if not approved:
            return update.context.bot.send_message(chat_id=chat_id, text=reason)

        # approved, we can prepare the transaction
        spending = maximum
        if requested_amount != 'max':
            spending = requested_amount

        # check if there are locked outputs
        spendable = self.walletQuerySpendable()
        if spending > spendable:
            reply_text = t('slateboy.msg_withdraw_locked')
            return update.context.bot.send_message(chat_id=chat_id, text=reply_text)

        # perform the transaction
        success, slatepack, txid = self.walletWithdraw()
        if not success:
            reply_text = t('slateboy.msg_withdraw_wallet_error')
            return update.context.bot.send_message(chat_id=chat_id, text=reply_text)

        # lock the amount
        success, reason = self.callback_withdraw_lock(update, context, spending, txid)
        if not success:
            return update.context.bot.send_message(chat_id=chat_id, text=reason)

        # proceed with the slatepack exchange
        update.context.bot.send_message(chat_id=chat_id, text=slatepack)
        reply_text = t('slateboy.msg_withdraw_instructions')
        update.context.bot.send_message(chat_id=chat_id, text=reply_text)


    def handlerRequestDeposit(self, update, context):
        chat_id = update.message.chat.id

        # get the amount if provided
        deposited_amount = None
        if len(context.args) > 0:
            try:
                deposited_amount = float(context.args[0])
            except ValueError:
                reply_text = t('slateboy.msg_deposit_invalid_amount').format(
                    context.args[0])
                return update.context.bot.send_message(
                    chat_id=chat_id, text=reply_text)

        # check if user can deposit
        approved, reason = self.callback_deposit(update, context, offered_amount)

        if not approved:
            return update.context.bot.send_message(chat_id=chat_id, text=reason)

        # proceed with the deposit
        if deposited_amount is None:
            # send instructions to the user for the SRS flow
            reply_text = t('slateboy.msg_deposit_srs_instructions')
            return update.context.bot.send_message(chat_id=chat_id, text=reply_text)

        # send instructions to the user for the RSR
        success, slatepack, txid = self.walletReceipt(deposited_amount)
        if not success:
            reply_text = t('slateboy.msg_deposit_rsr_wallet_error')
            return update.context.bot.send_message(chat_id=chat_id, text=reply_text)

        # lock the amount
        success, reason = self.callback_deposit_lock(update, context, deposited_amount, txid)
        if not success:
            return update.context.bot.send_message(chat_id=chat_id, text=reason)

        update.context.bot.send_message(chat_id=chat_id, text=slatepack)
        reply_text = t('slateboy.msg_deposit_rsr_instructions')
        update.context.bot.send_message(chat_id=chat_id, text=reply_text)


    def handlerBalance(self, update, context):
        chat_id = update.message.chat.id

        # get the balance
        success, reason, balance = self.callback_balance(update, context)
        if not success:
            # probably data was not correctly initiated, break!
            return update.context.bot.send_message(chat_id=chat_id, text=reason)

        spendable, confirming, locked = balance

        reply_text = t('slateboy.msg_balance').format(
            str(spendable), str(confirming), str(locked))
        update.context.bot.send_message(chat_id=chat_id, text=reply_text)


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


    def jobAccounting(self, context):
        self.callback_job_accounting(context, self.config_job_accounting)


    # GRIN wallet methods
    def walletQueryConfirmed(self, txid):
        # TODO
        # status is confirmed, confirming or canceled
        # operation deposit or withdrawal
        return status, operation, 0

    def walletDecodeSlatepack(self, slatepack):
        # TODO
        pass

    def walletQuerySpendable(self):
        # TODO
        pass

    def walletWithdraw(self):
        # TODO
        success = True
        slatepack = ''
        txid = ''
        return success, slatepack, txid

from __future__ import unicode_literals

import re

from telegram.ext import Updater, CommandHandler, MessageHandler
from i18n.translator import t


# by default, we store user balance in the user context
def default_balance(self, update, context):
    # spendable, confirming, locked
    default_balance = (0, 0, 0)

    # check if context initiated
    if self.namespace not in context.user_data.keys():
        success = False
        reason = t('slateboy.msg_missing_user_context')
        return success, reason, default_balance

    user_data = context.user_data[self.namespace]

    # check if user has balance initiated
    if 'balance' not in user_data.keys():
        success = False
        reason = t('slateboy.msg_missing_user_context')
        return success, reason, default_balance

    # check if user has balance initiated
    if 'txs' not in user_data.keys():
        success = False
        reason = t('slateboy.msg_missing_user_context')
        return success, reason, default_balance

    # all the data is there
    success = True
    reason = None
    balance = user_data['balance']
    return success, reason, balance


# by default, we lock the user balance in the user context
def default_callback_withdraw_lock(self, update, context, amount, txid):
    # get the balance
    success, reason, balance = self.callback_balance(update, context)
    if not success:
        # probably data was not correctly initiated, break!
        return success, reason

    # check if user has balance
    spendable, confirming, locked = balance

    # lock
    balance = spendable - amount, confirming, locked + amount
    context.user_data[self.namespace]['balance'] = balance
    context.user_data[self.namespace]['txs'].append(txid)

    success = True
    reason = None
    return success, reason


# by default, we lock the user balance in the user context
def default_callback_deposit_lock(self, update, context, amount, txid):
    # get the balance
    success, reason, balance = self.callback_balance(update, context)
    if not success:
        # probably data was not correctly initiated, break!
        return success, reason

    # check if user has balance
    spendable, confirming, locked = balance

    # lock
    balance = spendable, confirming, locked + amount
    context.user_data[self.namespace]['balance'] = balance
    context.user_data[self.namespace]['txs'].append(txid)

    success = True
    reason = None
    return success, reason


# by default, we check if txid is in the user context
def default_is_txid_known(self, update, context, txid):
    found = False

    # get the balance
    success, reason, balance = self.callback_balance(update, context)
    if not success:
        # probably data was not correctly initiated, break!
        return success, reason, found

    # check if txid is known
    if txid in context.user_data[self.namespace]['txs']:
        found = True

    success = True
    reason = None
    return success, reason, found



# by default we withdraw from the user context if there is sufficient balance
def default_callback_withdraw(self, update, context, requested_amount):
    approved = False
    reason = None
    maximum = None

    # get the balance
    success, reason, balance = self.callback_balance(update, context)
    if not success:
        # probably data was not correctly initiated, break!
        return approved, reason, maximum

    # check if user has balance
    spendable, confirming, locked = balance

    # user can withdraw as much as spendable
    maximum = spendable

    # check if requested less than spendable
    if requested_amount == 'max':
        if maximum == 0:
            approved = False
            reason = t('slateboy.msg_withdraw_no_balance')
            return approved, reason, maximum

        # everything is valid
        approved = True
        reason = None
        return approved, reason, maximum

    # checking specific amount
    if requested_amount > maximum:
        if requested_amount <= spendable + confirming:
            approved = False
            reason = t('slateboy.msg_withdraw_wait_confirmation')
            return approved, reason, maximum
        else:
            approved = False
            reason = t('slateboy.msg_withdraw_insufficient_balance')
            return approved, reason, maximum

    # everything is fine
    approved = True
    reason = None
    return approved, reason, maximum


# by default we approve all the deposits
def default_callback_deposit(self, update, context, offered_amount):
    approved = True
    reason = None
    return approved, reason


class SlateBoy:
    def __init__(self, name, api_key, namespace,
                 callback_balance=default_balance,
                 callback_withdraw=default_callback_withdraw,
                 callback_withdraw_lock=default_callback_withdraw_lock,
                 callback_deposit=default_callback_deposit,
                 callback_is_txid_known=default_is_txid_known):
        self.name = name
        self.api_key = api_key
        self.namespace = namespace

        # register callbacks
        self.callback_balance = callback_balance
        self.callback_withdraw = callback_withdraw
        self.callback_withdraw_lock = callback_withdraw_lock
        self.callback_deposit = callback_deposit
        self.callback_is_txid_known = callback_is_txid_known


    def initiate(self):
        self.updater = Updater(self.api_key, use_context=True)
        self.updater.dispatcher.add_handler(
            CommandHandler('withdraw', self.handlerRequestWithdraw))
        self.updater.dispatcher.add_handler(
            CommandHandler('deposit', self.handlerRequestDeposit))
        self.updater.dispatcher.add_handler(
            CommandHandler('balance', self.handlerBalance))

        # for handling slatepacks
        self.updater.dispatcher.add_handler(
            MessageHandler(Filters.text, self.genericTextHandler))


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


    # GRIN wallet methods
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

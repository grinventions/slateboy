from i18n.translator import t

from slateboy.helpers import getNow


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


# by default just iterate users context
def default_callback_job_txs(self, context, callback_function_tx, config_job_txs):
    found_confirmed = {}

    # iterate over users
    for user_id, user_data in context.dispatcher.user_data.items():
        for txid in user_data[self.namespace]['txs']:
            # the callback function will inform
            status, operation, amount = callback_function_tx(txid)

            # should it be removed?
            if status in ['confirmed', 'canceled']:
                if user_id not in found_confirmed.keys():
                    found_confirmed[user_id] = []
                found_confirmed[user_id].append(txid)

            # check how the balance should be updated
            spendable, confirming, locked = user_data['balance']
            updated_balance = None

            if status == 'confirmed' and operation == 'deposit':
                updated_balance = spendable + amount, confirming - amount, locked

            if status == 'confirmed' and operation == 'withdrawal':
                updated_balance = spendable, confirming, locked - amount

            if status == 'canceled' and operation == 'deposit':
                updated_balance = spendable, confirming - amount, locked

            if status == 'canceled' and operation == 'withdrawal':
                updated_balance = spendable + amount, confirming, locked - amount

            context.dispatcher.user_data['balance'] = updated_balance

    # clean-up
    for user_id, confirmed_transactions in found_confirmed.items():
        for txid in confirmed_transactions:
            context.dispatcher.user_data[user_id]['txs'].remove(txid)


# by default we charge monthly fee to anyone who has balance higher than certain
# threshold, this will force users to not use the bot as their wallet
# and make them withdraw often
def default_callback_job_accounting(self, context, config_job_accounting):
    accounting_max_free_balance = config_job_accounting.get('max_free_balance', 10.0)
    accounting_period = config_job_accounting.get('period', 2629800)
    accounting_period_warning = config_job_accounting.get('period_warning', 2160000)
    accounting_monthly_charge = config_job_accounting.get('monthly_charge', 1.0)

    now = getNow()

    # check users
    for user_id, user_data in context.dispatcher.user_data.items():
        ts = user_data['ts']
        spendable, confirming, locked = user_data['balance']

        # handle billing for custodian services
        if spendable + confirming > accounting_max_free_balance:
            warned = user_data.get('warned', False)
            if accounting_period_warning < now - ts < accounting_monthly_charge:
                if not warned:
                    reply_text = t('slateboy.msg_free_balance_warning').format(
                        str(spendable + confirming),
                        str(spendable),
                        str(confirming),
                        str(locked),
                        str(accounting_max_free_balance))
                    context.bot.send_message(
                        chat_id=user_id,
                        text=reply_text)
                    context.dispatcher.user_data[user_id]['warned'] = True
            elif accounting_monthly_charge <= now - ts:
                if not warned:
                    reply_text = t('slateboy.msg_free_balance_exceeded').format(
                        str(spendable + confirming),
                        str(spendable),
                        str(confirming),
                        str(locked),
                        str(accounting_max_free_balance))
                    context.bot.send_message(
                        chat_id=user_id,
                        text=reply_text)
                    context.dispatcher.user_data[user_id]['warned'] = spendable - accounting_monthly_charge, confirming, locked
                    context.bot.bot_data['charged'] += accounting_monthly_charge
                    del context.dispatcher.user_data[user_id]['warned']

    # handle inactive user context
    if UserBehavior.INACTIVITY in self.policy_user_context_attempt_destroy:
        accounting_balanceless_inactivity = config_job_accounting.get('balanceless_inactivity', 3600)
        balanceless = []
        for user_id, user_data in context.dispatcher.user_data.items():
            ts = user_data['ts']
            spendable, confirming, locked = user_data['balance']

            if spendable == 0 and confirming == 0 and locked == 0 and now - ts > accounting_balanceless_inactivity:
                balanceless.append(user_id)

        # attempt removal of the balanceless users context
        for user_id in balanceless:
            # TODO here attempt to destroy the user context
            pass


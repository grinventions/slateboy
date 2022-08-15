from i18n.translator import t

from slateboy.personality import BlankPersonality


# a bot capable only deposits, withdrawals and displaying
# the EULA, it stores value in the bot context
# which can be made persistent if needed
class ContextBlankPersonality(BlankPersonality):
    def __init__(self, slateboy, namespace,
                 admins=[], EULA_key='', EULA_version=''):
        self.parent.__init__(self, slateboy)

        # namespace key for the user and bot session
        self.namespace = namespace

        # admins
        self.admins = admins
        self.validateAdmins()

        # EULA
        self.EULA_key = EULA
        self.EULA_version = EULA_version

    #
    # utility methods
    #

    # if you have custom logic for handling admins you may override this method
    def validateAdmins(self, admins):
        if len(self.admins) == 0:
            raise ValueError('There needs to be at least one admin')

    # checking if user context data structure is initiated
    def isUserContextInitiated(self, context, user_id):
        # check if context initiated
        if self.namespace not in context.user_data.keys():
            success = False
            reason = t('slateboy.msg_missing_user_context')
            return success, reason

        user_data = context.user_data[self.namespace][user_id]

        # check if user has balance initiated
        if 'balance' not in user_data.keys():
            success = False
            reason = t('slateboy.msg_missing_user_context')
            return success, reason

        # check if user has transactions initiated
        if 'txs' not in user_data.keys():
            success = False
            reason = t('slateboy.msg_missing_user_context')
            return success, reason

        # everything is there
        success = True
        reason = None
        return success, reason

    # initiating the user context data structure
    def initUserContext(self, context, user_id):
        # check if context initiated
        is_initiated, _ = self.isUserContextInitiated(context, user_id)
        if is_initiated:
            success = False
            reason = t('slateboy.msg_user_context_already_initiated')
            return success, reason

        # spendable, confirming, locked
        _default_balance = (0, 0, 0, 0)

        context.user_data[self.namespace][user_id]['balance'] = _default_balance
        context.user_data[self.namespace][user_id]['txs'] = []
        context.user_data[self.namespace][user_id]['EULA'] = None

        # done
        success = True
        reason = None
        return success, reason

    # checking if bot context data structure is initiated
    def isBotContextInitiated(self, context, update=None):
        # check if context initiated
        if self.namespace not in context.bot_data.keys():
            success = False
            reason = t('slateboy.msg_missing_bot_context')
            return success, reason

        bot_data = context.bot_data[self.namespace]

        # check if bot has balance initiated
        if 'balance' not in bot_data.keys() or 'txs' not in bot_data.keys():
            success = False
            reason = t('slateboy.msg_missing_bot_context')
            return success, reason

        # everything is there
        success = True
        reason = None
        return success, reason

    # initiating the user context data structure
    def initBotContext(self, context, update=None):
        # check if context initiated
        is_initiated, _ = self.isBotContextInitiated(update, context)
        if is_initiated:
            success = False
            reason = t('slateboy.msg_bot_context_already_initiated')
            return success, reason

        context.bot_data[self.namespace]['balance'] = 0
        context.bot_data[self.namespace]['txs'] = {}

        # done
        success = True
        reason = None
        return success, reason

    # helper function to check balance of particular user
    def getUserBalance(self, context, user_id):
        # check if context initiated
        is_initiated, _ = self.isUserContextInitiated(context, user_id)
        if is_initiated:
            success = False
            reason = t('slateboy.msg_user_context_not_initiated')
            return success, reason, balance

        # done, return the balance
        success = True
        reason = None
        balance = context.user_data[self.namespace]['balance']
        return success, reason, balance

    # helper function to check balance of the bank
    def getBankBalance(self, context, user_id):
        # check if context initiated
        is_initiated, _ = self.isBotContextInitiated(context)
        if is_initiated:
            success = False
            reason = t('slateboy.msg_bot_context_not_initiated')
            return success, reason, balance

        # done, return the balance
        success = True
        reason = None
        balance = context.user_data[self.namespace]['balance']
        return success, reason, balance

    def assignTx(self, context, user_id, tx_id):
        context.bot_data[self.namespace]['txs'][tx_id] = str(user_id)
        context.user_data[self.namespace][user_id]['txs'].append(tx_id)

    def unassignTx(self, context, user_id, tx_id):
        del context.bot_data[self.namespace]['txs'][tx_id]
        context.user_data[self.namespace][user_id]['txs'].remove(tx_id)

    def isTx(self, context, tx_id):
        if tx_id in context.bot_data[self.namespace]['txs'].keys():
            raise ValueError('Invalid Transaction')

        # yes!
        return True

    def isTxValid(self, context, user_id, tx_id):
        if tx_id in context.user_data[self.namespace][user_id]['txs']:
            raise ValueError('Invalid Transaction')

        # yes!
        return True

    #
    # bot interface methods
    #

    # getting the balance
    def getBalance(self, update, context):
        # get the user_id
        user_id = update.message.from_user.id

        # get the balance
        success, reason, balance = getUserBalance(self, context, user_id)
        if not success:
            return update.context.bot.send_message(chat_id=chat_id, text=reason)

        # all done!
        return success, reason, balance

    # deposit behavior

    # by default we just accept all the deposits
    def canDeposit(self, update, context, amount):
        # get the user_id
        user_id = update.message.from_user.id

        # make sure user does have a valid context
        # if not, simply create it
        is_initiated, _ = self.isUserContextInitiated(context, user_id)
        if not is_initiated:
            self.initUserContext(context, user_id)

        # all done!
        success = True
        reason = None
        result = True
        return success, reason, result

    def assignDepositTx(self, update, context, amount, tx_id):
        # get the user_id
        user_id = update.message.from_user.id

        # check if this transaction has already been assigned
        if tx_id in context.bot_data[self.namespace]['txs'].keys():
            success = False
            reason = t('slateboy.msg_tx_already_assigned')
            reply_text = None
            return success, reason, reply_text

        # assign user
        context.bot_data[self.namespace]['txs'][tx_id] = str(user_id)
        context.user_data[self.namespace][user_id]['txs'].append(tx_id)

        # fetch the balance
        success, reason, balance = getUserBalance(self, context, user_id)
        spendable, awaiting_confirmation, awaiting_finalization, locked = balance

        # requested a deposit, make it awaiting finalization
        awaiting_finalization += amount

        # update the balance
        balance = spendable, awaiting_confirmation, awaiting_finalization, locked
        context.user_data[self.namespace]['balance'] = balance

        # all done!
        success = True
        reason = None
        reply_text = t('slateboy.msg_deposit_assigned').format(
            str(spendable), str(awaiting_confirmation),
            str(awaiting_finalization), str(locked))
        return success, reason, reply_text

    def finalizeDepositTx(self, update, context, amount, tx_id):
        # get the user_id
        user_id = update.message.from_user.id

        # validate this tx for given user
        self.isTxValid(context, user_id, tx_id)

        # fetch the balance
        success, reason, balance = getUserBalance(self, context, user_id)
        spendable, awaiting_confirmation, awaiting_finalization, locked = balance

        # the deposit was finalized, move it to awaiting finalization
        awaiting_confirmation += amount
        awaiting_finalization -= amount

        # update the balance
        balance = spendable, awaiting_confirmation, awaiting_finalization, locked
        context.user_data[self.namespace]['balance'] = balance

        # all done!
        success = True
        reason = None
        reply_text = t('slateboy.msg_deposit_finalized').format(
            str(spendable), str(awaiting_confirmation),
            str(awaiting_finalization), str(locked))
        return success, reason, reply_text

    def confirmDepositTx(self, context, amount, tx_id):
        # check if this tx exists
        self.isTx(context, tx_id)

        # fetch user ID from the index
        user_id = context.bot_data[self.namespace]['txs'][tx_id]

        # validate this tx for given user
        self.isTxValid(context, user_id, tx_id)

        # fetch the balance
        success, reason, balance = getUserBalance(self, context, user_id)
        spendable, awaiting_confirmation, awaiting_finalization, locked = balance

        # the deposit is confirmed, make it spendable
        spendable += amount
        awaiting_confirmation -= amount

        # update the balance
        balance = spendable, awaiting_confirmation, awaiting_finalization, locked
        context.user_data[self.namespace]['balance'] = balance

        # remove this transaction ID from the index
        self.unassignTx(context, user_id, tx_id)

        # all done!
        success = True
        reason = None
        reply_text = t('slateboy.msg_deposit_confirmed').format(
            str(spendable), str(awaiting_confirmation),
            str(awaiting_finalization), str(locked))
        return success, reason, reply_text

    def cancelDepositTx(self, context, amount, tx_id, update=False):
        # check if this tx exists
        self.isTx(context, tx_id)

        # fetch user ID from the index
        user_id = context.bot_data[self.namespace]['txs'][tx_id]

        # validate this tx for given user
        self.isTxValid(context, user_id, tx_id)

        # fetch the balance
        success, reason, balance = getUserBalance(self, context, user_id)
        spendable, awaiting_confirmation, awaiting_finalization, locked = balance

        # the deposit failed, the amount is not longer awaiting finalization
        awaiting_finalization -= amount

        # update balances
        balance = spendable, awaiting_confirmation, awaiting_finalization, locked
        context.user_data[self.namespace]['balance'] = balance

        # remove this transaction ID from the index
        self.unassignTx(context, user_id, tx_id)

        # all done!
        success = True
        reason = None
        reply_text = t('slateboy.msg_deposit_canceled').format(
            str(spendable), str(awaiting_confirmation),
            str(awaiting_finalization), str(locked))
        return success, reason, reply_text

    # withdraw behavior
    def canWithdraw(self, update, context, requested_amount, maximum=False):
        chat_id = update.message.chat.id
        user_id = update.message.from_user.id

        is_initiated, reason = self.isUserContextInitiated(context, user_id)
        if not is_initiated:
            success = False
            result = None
            approved_amount = None
            return success, reason, approved_amount

        success, reason, balance = getUserBalance(self, context, user_id)
        spendable, awaiting_confirmation, awaiting_finalization, locked = balance

        if maximum:
            success = True
            reason = None
            result = True
            approved_amount = spendable
            return success, reason, approved_amount

        if requested_amount > spendable:
            success = True
            reason = None
            result = False
            approved_amount = spendable
            return success, reason, result, approved_amount

        result = True
        approved_amount = requested_amount

        # all done!
        success = True
        reason = None
        return success, reason, result, approved_amount

    def assignWithdrawTx(self, update, context, amount, tx_id):
        # get the user_id
        user_id = update.message.from_user.id

        # check if this transaction has already been assigned
        if tx_id in context.bot_data[self.namespace]['txs'].keys():
            raise Exception('Transaction already assigned')

        # assign this tx to the user
        self.assignTx(context, user_id, tx_id)

        # fetch the balance
        success, reason, balance = getUserBalance(self, context, user_id)
        spendable, awaiting_confirmation, awaiting_finalization, locked = balance

        # attempting to withdraw, locking the amount
        spendable -= amount
        locked += amount

        # update balances
        balance = spendable, awaiting_confirmation, awaiting_finalization, locked
        context.user_data[self.namespace]['balance'] = balance

        # all done!
        success = True
        reason = None
        send_instructions = True
        reply_text = t('slateboy.msg_withdraw_assigned').format(
            str(spendable), str(awaiting_confirmation),
            str(awaiting_finalization), str(locked))
        return success, reason, send_instructions, reply_text

    def finalizeWithdrawTx(self, update, context, amount, tx_id):
        # get the user_id
        user_id = update.message.from_user.id

        # validate this tx for given user
        self.isTxValid(context, user_id, tx_id)

        # all done!
        success = True
        reason = None
        reply_text = t('slateboy.msg_withdraw_finalized').format(
            str(spendable), str(awaiting_confirmation),
            str(awaiting_finalization), str(locked))
        return success, reason, reply_text

    def confirmWithdrawTx(self, context, amount, tx_id):
        # check if this tx exists
        self.isTx(context, tx_id)

        # fetch user ID from the index
        user_id = context.bot_data[self.namespace]['txs'][tx_id]

        # validate this tx for given user
        self.isTxValid(context, user_id, tx_id)

        # fetch the balance
        success, reason, balance = getUserBalance(self, context, user_id)
        spendable, awaiting_confirmation, awaiting_finalization, locked = balance

        # confirmed so no longer locked
        locked -= amount

        # update the balance
        balance = spendable, awaiting_confirmation, awaiting_finalization, locked
        context.user_data[self.namespace]['balance'] = balance

        # remove this transaction ID from the index
        self.unassignTx(context, user_id, tx_id)

        # all done!
        success = True
        reason = None
        reply_text = t('slateboy.msg_withdraw_confirmed').format(
            str(spendable), str(awaiting_confirmation),
            str(awaiting_finalization), str(locked))
        return success, reason, reply_text

    def cancelWithdrawTx(self, context, amount, tx_id):
        # check if this tx exists
        self.isTx(context, tx_id)

        # fetch user ID from the index
        user_id = context.bot_data[self.namespace]['txs'][tx_id]

        # validate this tx for given user
        self.isTxValid(context, user_id, tx_id)

        # fetch the balance
        success, reason, balance = getUserBalance(self, context, user_id)
        spendable, awaiting_confirmation, awaiting_finalization, locked = balance

        # canceled the withdraw, moving from locked back to spendable
        locked -= amount
        spendable += amount

        # update the balance
        balance = spendable, awaiting_confirmation, awaiting_finalization, locked
        context.user_data[self.namespace]['balance'] = balance

        # remove this transaction ID from the index
        self.unassignTx(context, user_id, tx_id)

        # all done!
        success = True
        reason = None
        reply_text = t('slateboy.msg_deposit_canceled').format(
            str(spendable), str(awaiting_confirmation),
            str(awaiting_finalization), str(locked))
        return success, reason, reply_text

    # for the context bot we always approve and finalize unless
    # if tx is unknown
    def shouldFinalizeTx(self, update, context, tx_id):
        try:
            # check if this tx exists
            reason = None
            should_finalize = self.isTx(context, tx_id)
            return should_finalize, reason
        except ValueError:
            reason = t('slateboy.msg_unknown_tx')
            should_finalize = False
            return should_finalize, reason

    def shouldFinalizeDepositTx(self, update, context, tx_id):
        return self.shouldFinalizeTx(update, context, tx_id)

    def shouldFinalizeWithdrawTx(self, update, context, tx_id):
        return self.shouldFinalizeTx(update, context, tx_id)

    # EULA behavior

    # whether user has to see the terms and agreements
    def shouldSeeEULA(self, update, context):
        # get the user_id
        user_id = update.message.from_user.id

        # check most recent EULA signed by the user
        signed_version = context.user_data[self.namespace][user_id]['EULA']

        if signed_version is None:
            needs_to_see = True
            EULA = t(self.EULA_key)
            EULA_verion = self.EULA_version
            return needs_to_see, EULA, EULA_verion

        if signed_version != self.EULA_version:
            needs_to_see = True
            EULA = t(self.EULA_key)
            EULA_verion = self.EULA_version
            return needs_to_see, EULA, EULA_verion

        # looks like user has approved our terms
        # all done!
        needs_to_see = False
        EULA = None
        EULA_verion = self.EULA_version
        return needs_to_see, EULA, EULA_verion

    # we mark user has approved terms and agreement
    def approvedEULA(self, update, context):
        # get the user_id
        user_id = update.message.from_user.id

        # mark the approved EULA as the currently required one
        context.user_data[self.namespace][user_id]['EULA'] = self.EULA_version

        # all done!
        success = True
        reason = None
        return success, reason

    # we do not record EULA denials, simply ignore
    def deniedEULA(self, update, context):
        # all done!
        success = True
        reason = None
        return success, reason

    # Group behavior

    # if bot gets added to the group we check if was added by the admin
    # if not, bot will leave immediately
    def shouldLeave(self, update, context):
        # get the user_id
        user_id = update.message.from_user.id

        # bot will leave the group if added by a stranger
        if user_id not in self.admins:
            return True

        # bot was added by one of the admins
        # all done!
        return False

    # we want the bot to ignore other bots by default
    def shouldIgnore(self, update, context):
        # is the message coming from a bot?
        if update.message.from_user.is_bot:
            ignore = True
            reason = t('slateboy.msg_rejecting_bots')
            return ignore, reason

        # seems like we can let this flow continue...
        # all done!
        ignore = False
        reason = None
        return ignore, reason

from i18n.translator import t

from slateboy.personality import BlankPersonality


# a bot capable only deposits, withdrawals and displaying
# the EULA, it stores value in the bot context
# which can be made persistent if needed
class ContextBlankPersonality(BlankPersonality):
    def __init__(self, slateboy, namespace,
                 EULA='', EULA_version=''):
        self.parent.__init__(self, slateboy)

        # namespace key for the user and bot session
        self.namespace = namespace

        # EULA
        self.EULA = EULA
        self.EULA_version = EULA_version

    #
    # utility methods
    #

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
        _default_balance = (0, 0, 0)

        context.user_data[self.namespace][user_id]['balance'] = _default_balance
        context.user_data[self.namespace][user_id]['txs'] = []

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
        if 'balance' not in bot_data.keys():
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

        # spendable, confirming, locked
        _default_balance = 0
        context.user_data[self.namespace]['balance'] = _default_balance

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

    #
    # bot interface methods
    #

    # getting the balance
    def getBalance(self, update, context):
        chat_id = update.message.chat.id
        user_id = update.message.from_user.id

        success, reason, balance = getUserBalance(self, context, user_id)
        if not success:
            return update.context.bot.send_message(chat_id=chat_id, text=reason)

        spendable, confirming, locked = balance
        reply_text = t('slateboy.msg_balance').format(
            str(spendable), str(confirming), str(locked))
        return update.context.bot.send_message(chat_id=chat_id, text=reply_text)

class BlankPersonality:
    def __init__(self, slateboy):
        self.slateboy = slateboy

    # getting the balance
    # returns one of the following types
    #
    # (int, int, int, int)
    # (spendable, awaiting_confirmation, awaiting_finalization, locked)
    # then it is assumed to be GRIN in IGNO unit
    #
    # (float, float, float, float)
    # (spendable, awaiting_confirmation, awaiting_finalization, locked)
    # then it is assumed to be GRIN in whole GRIN units
    #
    # str
    # formatted balance text ready for the user
    def getBalance(self, update, context):
        raise Exception('Unimplemented')

    # deposit behavior

    # (bool, str | None, bool, str | None)
    # (success, reason, result, reply_text)
    # success - whether execution was valid
    # reason - String or None, reason for failure
    # reply_text - Message to the user
    def canDeposit(self, update, context, amount):
        return True, None, True, None

    # puts amount as awaiting_finalization balance
    # (bool, str | None, str | None)
    # str is the formatted message to the user
    # it can contain {slatepack} tag to put the slatepack
    # inside of it, if the tag is not included, the slatepack
    # will be sent in the separate message
    def assignDepositTx(self, update, context, amount, tx_id):
        raise Exception('Unimplemented')

    # return bool and reason
    def shouldFinalizeDepositTx(self, update, context, tx_id):
        raise Exception('Unimplemented')

    # puts amount as awaiting_confirmation balance
    # returns (str)
    # str is the formatted message to the user
    def finalizeDepositTx(self, update, context, amount, tx_id):
        raise Exception('Unimplemented')

    # moves amount from awaiting_confirmation to spendable balance
    # returns (str)
    # str is the formatted message to the user
    def confirmDepositTx(self, context, amount, tx_id, update=None):
        raise Exception('Unimplemented')

    # is called if user does not "pay" on time
    # removes amount from awaiting_finalization balance
    def cancelDeposit(self, context, amount, tx_id, update=None):
        raise Exception('Unimplemented')

    # withdraw behavior

    # (bool, str)
    # bool indicates whether user can withdraw the amount
    # str is the formatted message to the user
    def canWithdraw(self, update, context, amount):
        return True, None, True, None

    # moves amount from spendable balance to locked balance
    # returns (str)
    # str is the formatted message to the user
    # it can contain {slatepack} tag to put the slatepack
    # inside of it, if the tag is not included, the slatepack
    # will be sent in the separate message
    def assignWithdrawTx(self, update, context, tx_id):
        raise Exception('Unimplemented')

    # return bool and reason
    def shouldFinalizeWithdrawTx(self, update, context, tx_id):
        raise Exception('Unimplemented')

    # does not move any balance but it is a chance to format message
    # to the user
    # returns (str)
    # str is the formatted message to the user
    def finalizeWithdrawTx(self, update, context, amount, tx_id):
        raise Exception('Unimplemented')

    # moves amount from locked to spendable balance
    # returns (str)
    # str is the formatted message to the user
    def confirmWithdrawTx(self, context, amount, tx_id, update=None):
        raise Exception('Unimplemented')

    # is called if user does not "receive" on time
    # moves amount from locked back to spendable
    def cancelWithdrawTx(self, context, amount, tx_id, update=None):
        raise Exception('Unimplemented')

    # EULA behavior
    def shouldSeeEULA(self, update, context):
        return False

    def approvedEULA(self, update, context):
        pass

    def deniedEULA(self, update, context):
        pass

    # what to do if being added to the group, should leave it?
    def shouldLeave(self, update, context):
        return False

    # what to do if being messaged, should ignore?
    def shouldIgnore(self, update, context):
        return False

    # callback informing that bot left the group
    def leftGroup(self, update, context):
        pass

    # callback about incoming text
    # they respond with a boolean whether if SlateBoy
    # should continue processing the message
    # if they return False message will be ignored
    # even if contains slatepack preventing users
    # to do deposits and withdrawals!
    def incomingText(self, update, context, contains_slatepack: bool):
        return True

    def incomingTextDM(self, update, context, contains_slatepack: bool):
        return True

    def incomingTextGroup(self, update, context, contains_slatepack: bool):
        return True

    # bot messages in the pipeline
    def customDepositInstructions(self, update, context):
        send_instructions = False
        custom_instructions = None
        return send_instructions, custom_instructions

    def customDepositSlatepackFormatting(self, update, context):
        custom_slatepack_formatting = None
        return custom_slatepack_formatting

    def customDepositFinalMessage(self, update, context):
        custom_final_message = None
        return custom_final_message

    def customWithdrawInstructions(self, update, context):
        send_instructions = False
        custom_instructions = None
        return send_instructions, custom_instructions

    def customWithdrawSlatepackFormatting(self, update, context):
        custom_slatepack_formatting = None
        return custom_slatepack_formatting

    def customWithdrawFinalMessage(self, update, context):
        custom_final_message = None
        return custom_final_message

    # renaming standard commands
    def renameStandardCommands(self):
        return {}

    # registering custom commands
    def registerCustomCommands(self):
        return []

    # register custom jobs
    def registerCustomJobs(self):
        return []

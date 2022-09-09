# Slateboy the Slatepack Bot

The idea started as [GRIN tipping bot](https://forum.grin.mw/t/grin-bounty-suggestions/9866/2) and was funded with a bounty from the GRIN Community Council. While [working](https://forum.grin.mw/t/telegram-bot-progress-thread-by-renzokuken/9882/32) on this project several designes were considered. Eventually during the [meeting in Warsaw](https://forum.grin.mw/t/grin-sun-in-warsaw-gathering/9953/2) we realized we need more than just a tipping bot, this is when this idea became more than just a bot implementation but rather a framework for building GRIN bots with various functionalities.

Slateboy consists of three main components.

1. [Slateboy class](https://github.com/grinventions/slateboy/blob/main/slateboy/slateboy.py), which is a bot implementation that is capable of doing withdraws and deposits in GRIN cryptocurrency.
2. [Provider class](https://github.com/grinventions/slateboy/blob/main/slateboy/providers.py), which abstracts access to a running GRIN wallet. At the moment there will be just Owner API wallet, but in the future as [mimblewimble-py](https://github.com/grinventions/mimblewimble-py) will become advanced enough we might implement another provider class that would allow to have the wallet under same thread.
3. [Personality class](https://github.com/grinventions/slateboy/blob/main/slateboy/personality.py), you may implement your own bot with your own custom functionalities by extending this class. We provide a [context personality](https://github.com/grinventions/slateboy/blob/main/slateboy/contextbot.py) that stores the bot state in the Telegram context.

The bot contains a built-in mechanism forcing users to read the [EULA](https://en.wikipedia.org/wiki/End-user_license_agreement) before performing a deposit. It also has an accounting job that runs in the background and it can charge users for inactivity or for keeping too high balance. This feature is fully customizable and is meant to prevent users use Slateboy as wallet substitute.

Examples of various bots that can be build using Slateboy can be found in the examples section below.

## Examples

### Tipping bot

Include a custom command `/tip` that allows to transfer some GRIN to another member of the group. You can build this whole bot just by implementing a single method!

```python
from slateboy.contextbot import ContextBlankPersonality


class TippingBotPersonality(ContextBlankPersonality):
    def __init__(self, slateboy, namespace,
                 config={}, admins=[], EULA_key='', EULA_version=''):
        self.parent.__init__(self, slateboy)
        self.custom_commands += [('tip', self.handlerTip)]

    def handlerTip(self, update, context):
        message_id = update.message.message_id
        chat_id = update.message.chat.id
        user_id = update.message.from_user.id

        # check if user provided the amount
        if len(context.args) == 0:
            reply_text = 'How much should I send?'
            return context.bot.send_message(
                reply_to_message_id=message_id,
                chat_id=chat_id, text=reply_text)

        # parse the amount
        try:
            amount = float(context.args)
        except:
            reply_text = 'Invalid amount!'
            return context.bot.send_message(
                reply_to_message_id=message_id,
                chat_id=chat_id, text=reply_text)

        # check the recipient
        if not update.message.reply_to_message:
            reply_text = 'To whom should I transfer?'
            return context.bot.send_message(
                reply_to_message_id=message_id,
                chat_id=chat_id, text=reply_text)
        reply_to = update.message.reply_to_message.id
        recipient = update.message.reply_to_message.from_user.id

        # fetch the balance
        success, reason, balance = self.getUserBalance(self, context, user_id)
        spendable, awaiting_confirmation, awaiting_finalization, locked = balance

        if spendable < amount:
            reply_text = 'Insufficient balance...'
            return context.bot.send_message(
                reply_to_message_id=message_id,
                chat_id=chat_id, text=reply_text)

        # do the transfer
        success, reason, r_balance = self.getUserBalance(self, context, recipient)
        r_spendable, r_awaiting_confirmation, r_awaiting_finalization, r_locked = r_balance

        context.user_data[self.namespace][user_id]['balance'] = \
            spendable - amount,\
            awaiting_confirmation,\
            awaiting_finalization,\
            locked

        context.user_data[self.namespace][recipient]['balance'] = \
            spendable + amount,\
            awaiting_confirmation,\
            awaiting_finalization,\
            locked

        reply_text = 'Transfer successful!'
            return context.bot.send_message(
                reply_to_message_id=message_id,
                chat_id=chat_id, text=reply_text)
```

### Reward support bot

A bot that allows to donate GRIN to a Telegram message which could be claimed with perfmission of an admin by a person who resolves the question.

TODO

### Personal Telegram GRIN wallet

Sometimes you might like to have a slatepack-enabled wallet in your Telegram, for instance to withdraw out from the exchanges or mining pools.

TODO

### Paid group

If you like to start a Telegram group with paid membership in GRIN you may use Slateboy to collect the payments and kick out users who did not renew their membership.

TODO

## References

1. [how to access user context from a scheduled job](https://github.com/python-telegram-bot/python-telegram-bot/issues/3175)
2. [test tools](https://github.com/GauthamramRavichandran/ptbtest)

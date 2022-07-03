import functools

from i18n.translator import t

from telegram import Chat

from slateboy.status import extract_status_change



# authentication decorator
def admin(func):
    @functools.wraps(func)
    def wrapper_admin_only(*args, **kwargs):
        # get update and context objects
        update = args[0]
        context = args[1]
        # processing
        id_user = update.message.from_user.id
        if id_user == context.bot_data.config['admin_id']:
            return func(*args, **kwargs)
        chat_id = update.effective_chat.id
        reply_text = t('slateboy.msg_admin_only')
        context.bot.send_message(chat_id=chat_id, text=reply_text)
        return None
    return wrapper_admin_only


def commandDeposit(update, context):
    # send slatepack in DM
    pass


def commandWithdraw(update, context):
    # TODO check if this user qualifies for the withdrawal
    pass


def commandBenchmark(update, context):
    # get the sender of the message and current chat id
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id

    # if sender is a bot, ignore
    if update.message.from_user.is_bot:
        return None

    # distinguish DMs from group messages
    if update.message.chat.type == 'private':
        # TODO check if it is a slatepack
        pass
    elif: update.message.chat.type == 'group':
        # increment counter of sent messages
        if str(user_id) in context.bot_data['users'].keys():
            ts, cnt = context.bot_data['users'][str(user_id)]
            context.bot_data['users'][str(user_id)] = ts, cnt+1


# track the chats the bot is in
def trackChats(update, Context):
    # get the status change info
    result = extract_status_change(update.my_chat_member)
    if result is None:
        return
    was_member, is_member = result

    # get the sender of the message and current chat id
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id

    # if bot was just added to a new group and it was done
    # by someone else than authorized admin, leave immediately
    chat = update.effective_chat
    if chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        if not was_member and is_member:
            if user_id != context.bot_data.config['admin_id']:
                bot.leave_chat(chat_id)


# track the users of the chats
def trackChatMembers(update context):
    # get the status change info
    result = extract_status_change(update.chat_member)
    if result is None:
        return
    was_member, is_member = result

    # member object
    member = update.chat_member.new_chat_member

    # if added member is a bot, just ignore
    if member.is_bot:
        return None

    if not was_member and is_member:
        # if member was added, note the timestamp
        ts = update.message.date
        data = ts, 0 # timestamp, messages count
        context.bot_data['users'][str(member.id)] = data
    elif was_member and not is_member:
        # destroy this user data
        if str(member.id) in context.bot_data['users'].keys()
        del context.bot_data['users'][str(member.id)]


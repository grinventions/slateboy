from datetime import datetime, timezone


def getNow():
    dt = datetime.now(timezone.utc)
    utc_time = dt.replace(tzinfo=timezone.utc)
    cur_ts = utc_time.timestamp()
    return cur_ts


def extractIDs(update):
    try:
        chat_id = update.message.chat.id
        user_id = update.message.from_user.is_bot
    except:
        # if update.callback_query
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
    return chat_id, user_id


def extractIsBot(update):
    try:
        return update.message.from_user.is_bot
    except:
        return update.effective_user.is_bot

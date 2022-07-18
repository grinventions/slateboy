import functools
import logging
import re

from i18n.translator import t
from datetime import datetime
from telegram import Chat

from slateboy.status import extract_status_change


# decorator indicating human-only method
def human(func):
    @functools.wraps(func)
    def wrapper_human_only(*args, **kwargs):
        # get update and context objects
        update = args[0]
        context = args[1]
        # processing
        if update.message.from_user.is_bot:
            return None
        return func(*args, **kwargs)
    return wrapper_human_only


# decorator indicating admin-only method
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


# decorator indicating user is registered
def registered(func):
    @functools.wraps(func)
    def wrapper_faucet(*args, **kwargs):
        # get update and context objects
        update = args[0]
        context = args[1]
        # processing
        if 't' not in context.user_data.keys():
            return None
        if 'c' not in context.user_data.keys():
            return None
        if 'f' not in context.user_data.keys():
            return None

        # get record
        ts = context.user_data['t']
        cnt = context.user_data['c']
        faucet_request_message_id = context.user_data['f']
        args = tuple(list(args) + [ts, cnt, faucet_request_message_id])

        return func(*args, **kwargs)
    return wrapper_faucet


@human
def commandDeposit(update, context):
    # get the sender of the message and current chat id
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id

    # inform everyone of the donation in progress
    reply_text = t('slateboy.msg_donation_0')
    context.bot.send_message(
        chat_id=chat_id,
        text=reply_text,
        reply_to_message_id=update.message.message_id)

    # get the slatepack address
    slatepack_address = 'grin10987654321' # TODO

    # send the DMs
    reply_text = t('slateboy.msg_donation_1')
    context.bot.send_message(
        chat_id=user_id,
        text=reply_text)

    context.bot.send_message(
        chat_id=user_id,
        text=slatepack_address)

    reply_text = t('slateboy.msg_donation_2').format(slatepack_address)
    context.bot.send_message(
        chat_id=user_id,
        text=reply_text)


@human
@registered
def commandWithdraw(update, context, ts, cnt, faucet_request_message_id):
    # get the sender of the message and current chat id
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id

    if faucet_request_message_id is None:
        reply_text = t('slateboy.msg_missing_faucet_request')
        return context.bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            reply_to_message_id=update.message.message_id)

    if str(faucet_request_message_id) not in context.bot_data['requests']:
        reply_text = t('slateboy.msg_missing_faucet_request')
        return context.bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            reply_to_message_id=update.message.message_id)

    # check if the request was approved
    min_approvals = context.bot_data['config']['min_approvals']
    faucet_request_timestamp, _, approvals = context.bot_data['requests'][str(faucet_request_message_id)]

    if len(approvals) < min_approvals:
        reply_text = t('slateboy.msg_request_insufficient').format(
            str(len(approvals)), str(min_approvals), str(min_approvals - len(approvals)))
        return context.bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            reply_to_message_id=faucet_request)

    # approved, check if there are unlocked outputs
    locked = False # TODO
    if locked:
        reply_text = t('slateboy.msg_request_locked')
        return context.bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            reply_to_message_id=faucet_request)

    # get the slatepack
    slatepack = 'BEGINSLATEPACK 0987654321 ENDSLATEPACK' # TODO

    # inform everyone of the slatepack being sent
    reply_text = t('slateboy.msg_withdraw_0')
    context.bot.send_message(
        chat_id=chat_id,
        text=reply_text,
        reply_to_message_id=faucet_request)

    # send the DMs
    reply_text = t('slateboy.msg_withdraw_1')
    context.bot.send_message(
        chat_id=user_id,
        text=reply_text)

    reply_text = t('slateboy.msg_withdraw_1')
    context.bot.send_message(
        chat_id=user_id,
        text=slatepack)

    # mark the state as in processing
    cur_ts = update.message.date
    context.bot_data['withdrawals'][str(user_id)] = cur_ts


@human
@registered
def commandFaucet(update, context, ts, cnt, faucet_request_message_id):
    # get the sender of the message and current chat id
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id

    # user has to have a certain number of messages sent to the group
    req_min_cnt = context.bot_data['config']['req_min_cnt']
    if cnt < req_min_cnt:
        reply_text = t('slateboy.msg_violated_min_cnt').format(str(req_min_cnt))
        return context.bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            reply_to_message_id=update.message.message_id)

    # user has to be in the group for certain amount of time
    cur_ts = update.message.date
    req_min_ts = context.bot_data['config']['req_min_ts']
    if cur_ts - ts < req_min_ts:
        reply_text = t('slateboy.msg_violated_min_ts').format(str(req_min_ts))
        return context.bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            reply_to_message_id=update.message.message_id)

    # check if there already is one request
    if faucet_request is not None:
        reply_text = t('slateboy.msg_new_request_0')
        context.bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            reply_to_message_id=update.message.message_id)
        reply_text = t('slateboy.msg_new_request_1')
        return context.bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            reply_to_message_id=faucet_request)

    # create a new faucet request
    approvals = []
    faucet_request = update.message.message_id
    context.bot_data['users'][str(user_id)] = ts, cnt, faucet_request
    faucet_request_timestamp = cur_ts
    context.bot_data['requests'][str(faucet_request)] = faucet_request_timestamp, user_id, approvals

    # inform of the success
    reply_text = t('slateboy.msg_new_request')
    return context.bot.send_message(
        chat_id=chat_id,
        text=reply_text,
        reply_to_message_id=faucet_request)


@human
@registered
def commandFaucetStatus(update, context, ts, cnt, faucet_request_message_id):
    # get the sender of the message and current chat id
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id

    if faucet_request_message_id is None:
        reply_text = t('slateboy.msg_missing_faucet_request')
        return context.bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            reply_to_message_id=update.message.message_id)

    if str(faucet_request_message_id) not in context.bot_data['requests']:
        reply_text = t('slateboy.msg_missing_faucet_request')
        return context.bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            reply_to_message_id=update.message.message_id)

    # provide status of the current faucet request
    min_approvals = context.bot_data['config']['min_approvals']
    faucet_request_timestamp, _, approvals = context.bot_data['requests'][str(faucet_request_message_id)]

    if len(approvals) < min_approvals:
        reply_text = t('slateboy.msg_request_insufficient').format(
            str(len(approvals)), str(min_approvals), str(min_approvals - len(approvals)))
        return context.bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            reply_to_message_id=faucet_request)

    reply_text = t('slateboy.msg_request_sufficient').format(
            str(len(approvals)), str(min_approvals))
    return context.bot.send_message(
        chat_id=chat_id,
        text=reply_text,
        reply_to_message_id=update.message.message_id)


@human
@registered
def commandFaucetCancel(update, context, ts, cnt, faucet_request_message_id):
    # get the sender of the message and current chat id
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id

    if faucet_request_message_id is None:
        reply_text = t('slateboy.msg_missing_faucet_request')
        return context.bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            reply_to_message_id=update.message.message_id)

    # update user data
    context.bot_data['users'][str(user_id)] = ts, cnt, None

    # remove faucet record
    if str(faucet_request_message_id) in context.bot_data['requests'].keys():
        del context.bot_data['requests'][str(faucet_request_message_id)]

    reply_text = t('slateboy.msg_request_cancelled')
    return context.bot.send_message(
        chat_id=chat_id,
        text=reply_text,
        reply_to_message_id=update.message.message_id)


@human
@registered
def commandApprove(update, context, ts, cnt, faucet_request_message_id):
    # get the sender of the message and current chat id
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id

    # check if user responds to another message
    if update.message.reply_to_message is None:
        reply_text = t('slateboy.msg_approve_reply')
        return context.bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            reply_to_message_id=update.message.message_id)

    # check if there is a record for this message
    ref_faucet_request_message_id = update.message.reply_to_message
    ref_faucet_request_message_author = update.message.reply_to_message.from_user.id
    if str(ref_faucet_request_message_id) not in context.bot_data['requests'].keys():
        reply_text = t('slateboy.msg_missing_faucet_requests')
        return context.bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            reply_to_message_id=update.message.message_id)

    # user has to have a certain number of messages sent to the group
    min_cnt = context.bot_data['config']['min_cnt']
    if cnt < min_cnt:
        reply_text = t('slateboy.msg_violated_min_cnt').format(str(min_cnt))
        return context.bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            reply_to_message_id=update.message.message_id)

    # user has to be in the group for certain amount of time
    cur_ts = update.message.date
    min_ts = context.bot_data['config']['min_ts']
    if cur_ts - ts < in_ts:
        reply_text = t('slateboy.msg_violated_min_ts').format(str(min_ts))
        return context.bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            reply_to_message_id=update.message.message_id)

    # check if this user already approved
    faucet_request_timestamp, request_author, approvals = context.bot_data['requests'][str(faucet_request_message_id)]

    if user_id in approvals:
        reply_text = t('slateboy.msg_already_approved')
        return context.bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            reply_to_message_id=update.message.message_id)

    # check if faucet request is not too old
    max_request_age = context.bot_data['config']['max_request_age']
    if cur_ts - faucet_request_timestamp > max_request_age:
        # delete the faucet request
        del context.bot_data['requests'][str(ref_faucet_request_message_id)]

        # inform of the deletion
        reply_text = t('slateboy.msg_expired')
        return context.bot.send_message(
            chat_id=chat_id,
            text=reply_text,
            reply_to_message_id=update.message.message_id)

    # looks like user can approve, increase the approval counter
    approvals.append(user_id)
    context.bot_data['requests'][str(ref_faucet_request_message_id)] = faucet_request_timestamp, request_author, approvals

    # it all went smoothly
    reply_text = t('slateboy.msg_approval_successful')
    return context.bot.send_message(
        chat_id=chat_id,
        text=reply_text,
        reply_to_message_id=update.message.message_id)


@human
@registered
def commandBenchmark(update, context, ts, cnt, faucet_request_message_id):
    # get the sender of the message and current chat id
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id

    # distinguish DMs from group messages
    if update.message.chat.type == 'private':
        # check if it is a slatepack
        regex = 'BEGINSLATEPACK[\\s\\S]*\\sENDSLATEPACK'
        matches = re.search(regex, update.message.text, flags=re.DOTALL)
        if matches is not None:
            slatepack = matches.group(0)
            # check the meaning of the slatepack
            if str(user_id) in context.bot_data['withdrawals'].keys():
                # user is withdrawing, slatepack has to be finalized
                # TODO
                pass
            else:
                # user is donating, we need to run receive
                # TODO
                pass
    elif update.message.chat.type == 'group':
        # increment counter of sent messages
        context.user_data['c'] = cnt + 1


# track the chats the bot is in
def trackChats(update, context):
    logger = logging.getLogger()

    # get the status change info
    result = extract_status_change(update.my_chat_member)
    if result is None:
        return
    was_member, is_member = result

    # get the sender of the message and current chat id
    if not update.my_chat_member:
        return None

    chat_id = update.my_chat_member.chat.id
    user_id = update.my_chat_member.from_user.id

    # if bot was just added to a new group and it was done
    # by someone else than authorized admin, leave immediately
    chat = update.effective_chat
    if chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        if not was_member and is_member:
            if user_id != context.bot_data.get('config', {}).get('admin_id', None):
                logger.debug('Added to the group by someone else than admin, leaving...')
                context.bot.leave_chat(chat_id)
            else:
                logger.debug('Added to the group by the admin, staying...')
        else:
            logger.debug('Left a group...')


# track the users of the chats
def trackChatMembers(update, context):
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
        context.user_data['t'] = ts   # timestamp
        context.user_data['c'] = 0    # message count
        context.user_data['f'] = None # faucet request
    elif was_member and not is_member:
        # destroy this user data
        del context.user_data['t']
        del context.user_data['c']
        del context.user_data['f']


def cleanUpJob(context):
    # when is now?
    dt = datetime.now(timezone.utc)
    utc_time = dt.replace(tzinfo=timezone.utc)
    cur_ts = utc_time.timestamp()

    # remove expired requests
    cur_ts = update.message.date
    max_request_age = context.bot_data['config']['max_request_age']

    to_remove = []
    to_inform = []

    for faucet_request_id_str, (faucet_request_timestamp, request_author, approvals) in context.bot_data['requests'].items():
        if cur_ts - faucet_request_timestamp > max_request_age:
            to_remove.append(faucet_request_id_str)
            to_inform.append(request_author)

    for faucet_request_id_str, author in zip(to_remove, to_inform):
        del context.bot_data['requests'][faucet_request_id_str]
        ts, cnt, _ = context.bot_data['users'][str(author)]
        context.bot_data['users'][str(author)] = ts, cnt, None

        reply_text = t('slateboy.msg_expired_dm').format(str(max_request_age))
        context.bot.send_message(
            chat_id=author,
            text=reply_text)

    # check if expired withdrawals that keep outputs locked
    max_withdrawal_age = context.bot_data['config']['max_withdrawal_age']

    to_remove = []
    to_inform = []

    for author_str, withdrawal_ts in context.bot_data['withdrawals'].items():
        if cur_ts - withdrawal_ts > max_withdrawal_age:
            to_remove.append(author_str)
            to_inform.append(int(author_str))

    for author_str, author in zip(to_remove, to_inform):
        del context.bot_data['withdrawals'][author_str]

        reply_text = t('slateboy.msg_slatepack_expired')
        context.bot.send_message(
            chat_id=author,
            text=reply_text)

        # TODO cancel the tx

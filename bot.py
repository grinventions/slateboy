from __future__ import unicode_literals

import argparse
import logging
import yaml
import pathlib
import os

from datetime import datetime, time
from os.path import exists

from i18n import resource_loader
from i18n import config as i18config
from i18n.translator import t

from telegram.ext import Updater, CommandHandler, ChatMemberHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, Filters, PicklePersistence
from telegram import InlineKeyboardButton, KeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.error import BadRequest

from slateboy.handlers import commandDeposit, commandWithdraw
from slateboy.handlers import commandFaucet, commandFaucetStatus, commandFaucetCancel, commandApprove
from slateboy.handlers import commandBenchmark, trackChats, trackChatMembers, cleanUpJob

# parse the command line arguments
def parseConfigFile(filepath):
    if not exists(filepath):
        raise argparse.ArgumentTypeError('Provided configuration file does not exists')
    if not filepath.endswith('.yml'):
        raise argparse.ArgumentTypeError('Only .yml file types are currently supported for the configuration')
    return filepath

parser = argparse.ArgumentParser(description='Slateboy, the Telegram Slatepack Bot')
parser.add_argument('--config',
                    type=lambda x: parseConfigFile(x),
                    default=str(pathlib.Path(__file__).parent.absolute()) + '/config.yml',
                    help='Slatepack bot configuration file')
args = parser.parse_args()

# configuration
config = None
with open(args.config) as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

# logger
logfile = config['logfile']
logging.basicConfig(level=logging.ERROR,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename=logfile)
logger = logging.getLogger()
logger.setLevel(config.get('loglevel', 'ERROR'))

# translations
TRANSLATIONS_DIRECTORY = os.path.dirname(os.path.abspath(__file__)) + os.sep + 'translations' + os.sep
i18config.set('file_format', 'json')
i18config.set('load_path', [TRANSLATIONS_DIRECTORY])
i18config.set('filename_format', '{namespace}.{locale}.{format}')
i18config.set('locale', config['locale'])
i18config.set('fallback', config['fallback'])
resource_loader.init_json_loader()

# persistence
my_persistence = PicklePersistence(filename=config['persistence'])

# initiate the bot
updater = Updater(config['api_key'], persistence=my_persistence, use_context=True)

# Get the dispatcher to register handlers
dp = updater.dispatcher

# initiation function
def initiateBot(update, context):
    context.bot_data['config'].set(config)

# register handlers
dp.add_handler(CommandHandler('start', initiateBot))
dp.add_handler(CommandHandler('donate', commandDoposit))
dp.add_handler(CommandHandler('withdraw', commandWithdraw))
dp.add_handler(CommandHandler('approve', commandApprove))
dp.add_handler(CommandHandler('faucet', commandFaucet))
dp.add_handler(CommandHandler('status', commandFaucetStatus))
dp.add_handler(CommandHandler('cancel', commandFaucetCancel))

dp.add_handler(ChatMemberHandler(trackChats, ChatMemberHandler.MY_CHAT_MEMBER))
dp.add_handler(ChatMemberHandler(trackChatMembers, ChatMemberHandler.MY_CHAT_MEMBER))

dp.add_handler(MessageHandler(Filters.text, commandBenchmark))

# ready!
logger.info('Slatepack bot started...')
bot = updater.bot

job_queue = updater.job_queue
job_queue.run_repeating(cleanUpJob, interval=10*60*60, first=10*60*60)

updater.start_polling()
updater.idle()

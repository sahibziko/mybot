import html
from io import BytesIO
from typing import Optional, List
import random
import uuid
import re
import json
import time
import csv
import os
from time import sleep

from future.utils import string_types
from telegram.error import BadRequest, TelegramError, Unauthorized
from telegram import ParseMode, Update, Bot, Chat, User, MessageEntity, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram.utils.helpers import escape_markdown, mention_html, mention_markdown

from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, DEV_USERS, WHITELIST_USERS, GBAN_LOGS, LOGGER, spamfilters
from tg_bot.modules.helper_funcs.handlers import CMD_STARTERS
from tg_bot.modules.helper_funcs.misc import is_module_loaded, send_to_list
from tg_bot.modules.helper_funcs.chat_status import is_user_admin
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_unt_fedban, extract_user_fban
from tg_bot.modules.helper_funcs.string_handling import markdown_parser
from tg_bot.modules.disable import DisableAbleCommandHandler

import tg_bot.mod

# Hello bot owner, I spended for feds many hours of my life, Please don't remove this if you still respect MrYacha and peaktogoo and AyraHikari too
# Federation by MrYacha 2018-2019
# Federation rework by Mizukito Akito 2019
# Federation update v2 by Ayra Hikari 2019
# Time spended on feds = 10h by #MrYacha
# Time spended on reworking on the whole feds = 22+ hours by @peaktogoo
# Time spended on updating version to v2 = 26+ hours by @AyraHikari
# Total spended for making this features is 68+ hours
# LOGGER.info("Original federation module by MrYacha, reworked by Mizukito Akito (@peaktogoo) on Telegram.")

FBAN_ERRORS = {
"User is an administrator of the chat", "Chat not found",
"Not enough rights to restrict/unrestrict chat member",
"User_not_participant", "Peer_id_invalid", "Group chat was deactivated",
"Need to be inviter of a user to kick it from a basic group",
"Chat_admin_required",
"Only the creator of a basic group can kick group administrators",
"Channel_private", "Not in the chat", "Have no rights to send a message"
}

UNFBAN_ERRORS = {
"User is an administrator of the chat", "Chat not found",
"Not enough rights to restrict/unrestrict chat member",
"User_not_participant",
"Method is available for supergroup and channel chats only",
"Not in the chat", "Channel_private", "Chat_admin_required",
"Have no rights to send a message"
}


@run_async
def new_fed(update: Update, context: CallbackContext):
chat = update.effective_chat
user = update.effective_user
message = update.effective_message
if chat.type != "private":
update.effective_message.reply_text(
"Federasiya yaratmaq üçün mənimlə PM-də əlaqəyə keç.")
return
if len(message.text) == 1:
send_message(update.effective_message,
"Federesasiya üçün bir ad verməlisən!")
return
fednam = message.text.split(None, 1)[1]
if not fednam == '':
fed_id = str(uuid.uuid4())
fed_name = fednam
LOGGER.info(fed_id)

# Currently only for creator
#if fednam == 'Team Nusantara Disciplinary Circle':
#fed_id = "TeamNusantaraDevs"

x = sql.new_fed(user.id, fed_name, fed_id)
if not x:
update.effective_message.reply_text(
"Federasiyanı yaratmaq uğursuz oldu."
)
return

update.effective_message.reply_text("*Uğurla federasiya yaratdın!*"\
"\nAd: `{}`"\
"\nID: `{}`"
"\n\nAşağıdakı əmr ilə qruplarınızı fedə qoşa bilərsiniz:"
"\n`/joinfed {}`".format(fed_name, fed_id, fed_id), parse_mode=ParseMode.MARKDOWN)
try:
bot.send_message(
EVENT_LOGS,
"Yeni federasiya: <b>{}</b>\nID: <pre>{}</pre>".format(
fed_name, fed_id),
parse_mode=ParseMode.HTML)
except:
LOGGER.warning("Cannot send a message to EVENT_LOGS")
else:
update.effective_message.reply_text(
"Zəhmət olmasa aşağıda federasiya üçün ad yaz")


@run_async
def del_fed(update: Update, context: CallbackContext):
bot, args = context.bot, context.args
chat = update.effective_chat
user = update.effective_user
if chat.type != "private":
update.effective_message.reply_text(
"Federasiya silmək üçün PM-də əlaqəyə keç.")
return
if args:
is_fed_id = args[0]
getinfo = sql.get_fed_info(is_fed_id)
if getinfo is False:
update.effective_message.reply_text(
"Bu federasiya mövcud deyil.")
return
if int(getinfo['owner']) == int(user.id) or int(user.id) == OWNER_ID:
fed_id = is_fed_id
else:
update.effective_message.reply_text(
"Bunu yalnız federasiya sahibləri edə bilər!")
return
else:
update.effective_message.reply_text("Mən nəyi silməliyəmki?")
return

if is_user_fed_owner(fed_id, user.id) is False:
update.effective_message.reply_text(
"Bunu yalnız federasiya sahibləri edə bilər!")
return

update.effective_message.reply_text(
"Federasiyanı silmək istədiyindən əminsən? Bu geri qaytarıla bilməz, və '{}' həmişəlik silinəcək."
.format(getinfo['fname']),
reply_markup=InlineKeyboardMarkup([[
InlineKeyboardButton(
text="⚠️ Federasiyanı Sil ⚠️",
callback_data="rmfed_{}".format(fed_id))
], [InlineKeyboardButton(text="Cancel",
callback_data="rmfed_cancel")]]))


@run_async
def rename_fed(update, context):
user = update.effective_user
msg = update.effective_message
args = msg.text.split(None, 2)

if len(args) < 3:
return msg.reply_text("istifadəsi: /renamefed <fed_id> <newname>")

fed_id, newname = args[1], args[2]
verify_fed = sql.get_fed_info(fed_id)

if not verify_fed:
return msg.reply_text("Bu federasiya mənim database də yoxdur!")

if is_user_fed_owner(fed_id, user.id):
sql.rename_fed(fed_id, user.id, newname)
msg.reply_text(f"Federasiya adı yenisi ilə əvəz olundu. Yeni ad {newname}!")
else:
msg.reply_text("Bunu yalnız federasiya sahibləri edə bilər!")


@run_async
def fed_chat(update: Update, context: CallbackContext):
bot, args = context.bot, context.args
chat = update.effective_chat
user = update.effective_user
fed_id = sql.get_fed_id(chat.id)

user_id = update.effective_message.from_user.id
if not is_user_admin(update.effective_chat, user_id):
update.effective_message.reply_text(
"Bu əmri istifadə etmək üçün admin olmalısan.")
return

if not fed_id:
update.effective_message.reply_text(
"Bu qrup heç bir federasiyaya bağlı deyil!")
return

user = update.effective_user
chat = update.effective_chat
info = sql.get_fed_info(fed_id)

text = "Bu qrup aşağıdakı federasiyaya bağlıdır:"
text += "\n{} (ID: <code>{}</code>)".format(info['fname'], fed_id)

update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
def join_fed(update: Update, context: CallbackContext):
bot, args = context.bot, context.args
chat = update.effective_chat
user = update.effective_user

if chat.type == 'private':
send_message(update.effective_message,
"Bu əmri qrupda işlədin!")
return

message = update.effective_message
administrators = chat.get_administrators()
fed_id = sql.get_fed_id(chat.id)

if user.id in DRAGONS:
pass
else:
for admin in administrators:
status = admin.status
if status == "creator":
if str(admin.user.id) == str(user.id):
pass
else:
update.effective_message.reply_text(
"Bu əmri yalnız qrup sahibləri işlədə bilər!")
return
if fed_id:
message.reply_text("1 qrup 2 federasiyaya bağlı ola bilməz")
return

if len(args) >= 1:
getfed = sql.search_fed_by_id(args[0])
if getfed is False:
message.reply_text("Düzgün federasiya ID yazın")
return

x = sql.chat_join_fed(args[0], chat.title, chat.id)
if not x:
message.reply_text(
"Federasiyaya qoşulmaq uğursuz oldu!"
)
return

get_fedlog = sql.get_fed_log(args[0])
if get_fedlog:
if eval(get_fedlog):
bot.send_message(
get_fedlog,
"*{}* qrupu *{}* federasiyasına qoşuldu".format(
chat.title, getfed['fname']),
parse_mode="markdown")

message.reply_text("Bu qrup artıq {} federasiyasının 1 parçasıdır!".format(
getfed['fname']))


@run_async
def leave_fed(update: Update, context: CallbackContext):
bot, args = context.bot, context.args
chat = update.effective_chat
user = update.effective_user

if chat.type == 'private':
send_message(update.effective_message,
"Bu əmri qrupda işlədin!")
return

fed_id = sql.get_fed_id(chat.id)
fed_info = sql.get_fed_info(fed_id)

# administrators = chat.get_administrators().status
getuser = bot.get_chat_member(chat.id, user.id).status
if getuser in 'creator' or user.id in DRAGONS:
if sql.chat_leave_fed(chat.id) is True:
get_fedlog = sql.get_fed_log(fed_id)
if get_fedlog:
if eval(get_fedlog):
bot.send_message(
get_fedlog,
"*{}* qrupu artıq *{}* federasiyasının 1 parçası deyil".format(
chat.title, fed_info['fname']),
parse_mode="markdown")
send_message(
update.effective_message,
"Bu qrup artıq {} federasiyasının 1 parçası deyil!".format(
fed_info['fname']))
else:
update.effective_message.reply_text(
"Heç vaxt qoşulmadığın bir federasiyadan necə çıxa bilərsənki?!")
else:
update.effective_message.reply_text(
"Bu əmri yalnız qrup sahibləri işlədə bilər!")


@run_async
def user_join_fed(update: Update, context: CallbackContext):
bot, args = context.bot, context.args
chat = update.effective_chat
user = update.effective_user
msg = update.effective_message

if chat.type == 'private':
send_message(update.effective_message,
"Bu əmri qrupda işlədin!")
return

fed_id = sql.get_fed_id(chat.id)

if is_user_fed_owner(fed_id, user.id) or user.id in DRAGONS:
user_id = extract_user(msg, args)
if user_id:
user = bot.get_chat(user_id)
elif not msg.reply_to_message and not args:
user = msg.from_user
elif not msg.reply_to_message and (
not args or
(len(args) >= 1 and not args[0].startswith("@") and
not args[0].isdigit() and
not msg.parse_entities([MessageEntity.TEXT_MENTION]))):
msg.reply_text("Bu mesajdan istifadəçini əldə edə bilmədim")
return
else:
LOGGER.warning('error')
getuser = sql.search_user_in_fed(fed_id, user_id)
fed_id = sql.get_fed_id(chat.id)
info = sql.get_fed_info(fed_id)
get_owner = eval(info['fusers'])['owner']
get_owner = bot.get_chat(get_owner).id
if user_id == get_owner:
update.effective_message.reply_text(
"İstifadəçinin federasiya sahibi olduğunu bilirsiniz, hə? HƏ?"
)
return
if getuser:
update.effective_message.reply_text(
"Onsuzda federasiya admini olanları federasiya admini edə bilmərəm!"
)
return
if user_id == bot.id:
update.effective_message.reply_text(
"Mən onsuz da bütün federasiyalarda adminəm!")
return
res = sql.user_join_fed(fed_id, user_id)
if res:
update.effective_message.reply_text("Admin Edildi!")
else:
update.effective_message.reply_text("Admin edilə bilmədi!")
else:
update.effective_message.reply_text(
"Bunu yalnız federasiya sahibləri edə bilər!")


@run_async
def user_demote_fed(update: Update, context: CallbackContext):
bot, args = context.bot, context.args
chat = update.effective_chat
user = update.effective_user

if chat.type == 'private':
send_message(update.effective_message,
"Bu əmri qrupda işlədin!")
return

fed_id = sql.get_fed_id(chat.id)

if is_user_fed_owner(fed_id, user.id):
msg = update.effective_message
user_id = extract_user(msg, args)
if user_id:
user = bot.get_chat(user_id)

elif not msg.reply_to_message and not args:
user = msg.from_user

elif not msg.reply_to_message and (
not args or
(len(args) >= 1 and not args[0].startswith("@") and
not args[0].isdigit() and
not msg.parse_entities([MessageEntity.TEXT_MENTION]))):
msg.reply_text("Bu mesajdan istifadəçini əldə edə bilmədim")
return
else:
LOGGER.warning('error')

if user_id == bot.id:
update.effective_message.reply_text(
"Mənim adminliyimi alsan federasiya heçnə olar axı."
)
return

if sql.search_user_in_fed(fed_id, user_id) is False:
update.effective_message.reply_text(
"Federasiya admini olmayanların adminliyini ala bilmərəm!")
return

res = sql.user_demote_fed(fed_id, user_id)
if res is True:
update.effective_message.reply_text("Artıq federasiya admini deyil!")
else:
update.effective_message.reply_text("Adminliyini almaq uğursuz oldu!")
else:
update.effective_message.reply_text(
"Bunu yalnız federasiya sahibləri edə bilər!")
return


@run_async
def fed_info(update: Update, context: CallbackContext):
bot, args = context.bot, context.args
chat = update.effective_chat
user = update.effective_user
if args:
fed_id = args[0]
info = sql.get_fed_info(fed_id)
else:
fed_id = sql.get_fed_id(chat.id)
if not fed_id:
send_message(update.effective_message,
"Bu qrup heç bir federasiyaya bağlı deyil!")
return
info = sql.get_fed_info(fed_id)

if is_user_fed_admin(fed_id, user.id) is False:
update.effective_message.reply_text(
"Bunu yalnız federasiya adminləri edə bilər!")
return

owner = bot.get_chat(info['owner'])
try:
owner_name = owner.first_name + " " + owner.last_name
except:
owner_name = owner.first_name
FEDADMIN = sql.all_fed_users(fed_id)
TotalAdminFed = len(FEDADMIN)

user = update.effective_user
chat = update.effective_chat
info = sql.get_fed_info(fed_id)

text = "<b>ℹ️ Federasiya Haqqında:</b>"
text += "\nFedID: <code>{}</code>".format(fed_id)
text += "\nAd: {}".format(info['fname'])
text += "\nSahib: {}".format(mention_html(owner.id, owner_name))
text += "\nAdminlər: <code>{}</code>".format(TotalAdminFed)
getfban = sql.get_all_fban_users(fed_id)
text += "\nÜmumi fban sayı: <code>{}</code>".format(len(getfban))
getfchat = sql.all_fed_chats(fed_id)
text += "\nFederasiyaya bağlı olan qrupların sayı: <code>{}</code>".format(
len(getfchat))

update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
def fed_admin(update: Update, context: CallbackContext):
bot, args = context.bot, context.args
chat = update.effective_chat
user = update.effective_user

if chat.type == 'private':
send_message(update.effective_message,
"Bu əmri qrupda işlədin!")
return

fed_id = sql.get_fed_id(chat.id)

if not fed_id:
update.effective_message.reply_text(
"Bu qrup heç bir federasiyaya bağlı deyil!")
return

if is_user_fed_admin(fed_id, user.id) is False:
update.effective_message.reply_text(
"Bunu yalnız federasiya adminləri edə bilər!")
return

user = update.effective_user
chat = update.effective_chat
info = sql.get_fed_info(fed_id)

text = "<b>Federasiyas Adminləri {}:</b>\n\n".format(info['fname'])
text += "👑 Sahib:\n"
owner = bot.get_chat(info['owner'])
try:
owner_name = owner.first_name + " " + owner.last_name
except:
owner_name = owner.first_name
text += " • {}\n".format(mention_html(owner.id, owner_name))

members = sql.all_fed_members(fed_id)
if len(members) == 0:
text += "\n🔱 Bu qrupda Admin yoxdur"
else:
text += "\n🔱 Admin:\n"
for x in members:
user = bot.get_chat(x)
text += " • {}\n".format(mention_html(user.id, user.first_name))

update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
def fed_ban(update: Update, context: CallbackContext):
bot, args = context.bot, context.args
chat = update.effective_chat
user = update.effective_user

if chat.type == 'private':
send_message(update.effective_message,
"Bu əmri qrupda işlədin!")
return

fed_id = sql.get_fed_id(chat.id)

if not fed_id:
update.effective_message.reply_text(
"Bu qrup heç bir federasiyaya bağlı deyil!")
return

info = sql.get_fed_info(fed_id)
getfednotif = sql.user_feds_report(info['owner'])

if is_user_fed_admin(fed_id, user.id) is False:
update.effective_message.reply_text(
"Bunu yalnız federasiya adminləri edə bilər!")
return

message = update.effective_message

user_id, reason = extract_unt_fedban(message, args)

fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user_id)

if not user_id:
message.reply_text("Bir istifadəçiyə istinad etmirsiniz")
return

if user_id == bot.id:
message.reply_text(
"oh Mənsiz bir federasiya ola bilməz cnm.")
return

if is_user_fed_owner(fed_id, user_id) is True:
message.reply_text("Anlamadım niyə fban atırsanki bu şəxsə?")
return

if is_user_fed_admin(fed_id, user_id) is True:
message.reply_text("O federasiya adminidir, Onu fban etməyəcəm.")
return

if user_id == OWNER_ID:
message.reply_text("OHA ÇET NE DİYO BU? Botun Tanrısına fban atır 🆎🅾️!")
return

if int(user_id) in DRAGONS:
message.reply_text("Əjdahalar fban ala bilməz!")
return

if int(user_id) in TIGERS:
message.reply_text("Pələnglər fban ala bilməz!")
return

if int(user_id) in WOLVES:
message.reply_text("Wolves cannot be fed banned!")
return

if user_id in [777000, 1087968824]:
message.reply_text("Mal! Telegrama hücum çəkə bilmərsən!")
return

try:
user_chat = bot.get_chat(user_id)
isvalid = True
fban_user_id = user_chat.id
fban_user_name = user_chat.first_name
fban_user_lname = user_chat.last_name
fban_user_uname = user_chat.username
except BadRequest as excp:
if not str(user_id).isdigit():
send_message(update.effective_message, excp.message)
return
elif len(str(user_id)) != 9:
send_message(update.effective_message, "Bu bir istifadəçi deyil!")
return
isvalid = False
fban_user_id = int(user_id)
fban_user_name = "user({})".format(user_id)
fban_user_lname = None
fban_user_uname = None

if isvalid and user_chat.type != 'private':
send_message(update.effective_message, "Bu bir istifadəçi deyil!")
return

if isvalid:
user_target = mention_html(fban_user_id, fban_user_name)
else:
user_target = fban_user_name

if fban:
fed_name = info['fname']
#https://t.me/OnePunchSupport/41606 // https://t.me/OnePunchSupport/41619
#starting = "The reason fban is replaced for {} in the Federation <b>{}</b>.".format(user_target, fed_name)
#send_message(update.effective_message, starting, parse_mode=ParseMode.HTML)

#if reason == "":
# reason = "No reason given."

temp = sql.un_fban_user(fed_id, fban_user_id)
if not temp:
message.reply_text("Fban səbəbini güncəlləmək uğursuz oldu!")
return
x = sql.fban_user(fed_id, fban_user_id, fban_user_name, fban_user_lname,
fban_user_uname, reason, int(time.time()))
if not x:
message.reply_text(
"Fban etmək uğursuz oldu. Dəstək qrupumuza gəlin"
)
return

fed_chats = sql.all_fed_chats(fed_id)
# Will send to current chat
bot.send_message(chat.id, "<b>Fban Edildi</b>" \
"\n<b>Federasiya:</b> {}" \
"\n<b>Federasiya Admini:</b> {}" \
"\n<b>İstifadəçi:</b> {}" \
"\n<b>İstifadəçi ID:</b> <code>{}</code>" \
"\n<b>Səbəb:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
# Send message to owner if fednotif is enabled
if getfednotif:
bot.send_message(info['owner'], "<b>Fban Edildi</b>" \
"\n<b>Federasiya:</b> {}" \
"\n<b>Federasiya Admini:</b> {}" \
"\n<b>İstifadəçi:</b> {}" \
"\n<b>İstifadəçi ID:</b> <code>{}</code>" \
"\n<b>Səbəb:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
# If fedlog is set, then send message, except fedlog is current chat
get_fedlog = sql.get_fed_log(fed_id)
if get_fedlog:
if int(get_fedlog) != int(chat.id):
bot.send_message(get_fedlog, "<b>Fban Edildi</b>" \
"\n<b>Federasiya:</b> {}" \
"\n<b>Federasiya Admini:</b> {}" \
"\n<b>İstifadəçi:</b> {}" \
"\n<b>İstifadəçi ID:</b> <code>{}</code>" \
"\n<b>Səbəb:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
for fedschat in fed_chats:
try:
# Do not spam all fed chats
"""
bot.send_message(chat, "<b>FedBan reason updated</b>" \
"\n<b>Federation:</b> {}" \
"\n<b>Federation Admin:</b> {}" \
"\n<b>User:</b> {}" \
"\n<b>User ID:</b> <code>{}</code>" \
"\n<b>Reason:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
"""
bot.kick_chat_member(fedschat, fban_user_id)
except BadRequest as excp:
if excp.message in FBAN_ERRORS:
try:
dispatcher.bot.getChat(fedschat)
except Unauthorized:
sql.chat_leave_fed(fedschat)
LOGGER.info(
"{} qrup artıq {} federasiyasının 1 parçası deyil çünki qrupdan atıldım"
.format(fedschat, info['fname']))
continue
elif excp.message == "User_id_invalid":
break
else:
LOGGER.warning("{} istifadəçisini ban etmək uğursuz: {}".format(
chat, excp.message))
except TelegramError:
pass
# Also do not spam all fed admins
"""
send_to_list(bot, FEDADMIN,
"<b>FedBan reason updated</b>" \
"\n<b>Federation:</b> {}" \
"\n<b>Federation Admin:</b> {}" \
"\n<b>User:</b> {}" \
"\n<b>User ID:</b> <code>{}</code>" \
"\n<b>Reason:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), 
html=True)
"""

# Fban for fed subscriber
subscriber = list(sql.get_subscriber(fed_id))
if len(subscriber) != 0:
for fedsid in subscriber:
all_fedschat = sql.all_fed_chats(fedsid)
for fedschat in all_fedschat:
try:
bot.kick_chat_member(fedschat, fban_user_id)
except BadRequest as excp:
if excp.message in FBAN_ERRORS:
try:
dispatcher.bot.getChat(fedschat)
except Unauthorized:
targetfed_id = sql.get_fed_id(fedschat)
sql.unsubs_fed(fed_id, targetfed_id)
LOGGER.info(
"{} qrupu artıq {} federasiyasına abunə deyil çünki qrupdan atıldım"
.format(fedschat, info['fname']))
continue
elif excp.message == "User_id_invalid":
break
else:
LOGGER.warning(
"Unable to fban on {} because: {}".format(
fedschat, excp.message))
except TelegramError:
pass
#send_message(update.effective_message, "Fedban Reason has been updated.")
return

fed_name = info['fname']

#starting = "Starting a federation ban for {} in the Federation <b>{}</b>.".format(
# user_target, fed_name)
#update.effective_message.reply_text(starting, parse_mode=ParseMode.HTML)

#if reason == "":
# reason = "No reason given."

x = sql.fban_user(fed_id, fban_user_id, fban_user_name, fban_user_lname,
fban_user_uname, reason, int(time.time()))
if not x:
message.reply_text(
"Fban etmək uğursuzoldu."
)
return

fed_chats = sql.all_fed_chats(fed_id)
# Will send to current chat
bot.send_message(chat.id, "<b>Fban Edildi</b>" \
"\n<b>Federasiya:</b> {}" \
"\n<b>Federasiya Admini:</b> {}" \
"\n<b>İstifadəçi:</b> {}" \
"\n<b>İstifadəçi ID:</b> <code>{}</code>" \
"\n<b>Səbəb:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
# Send message to owner if fednotif is enabled
if getfednotif:
bot.send_message(info['owner'], "<b>Fban Edildi</b>" \
"\n<b>Federasiya:</b> {}" \
"\n<b>Federasiya Admini:</b> {}" \
"\n<b>İstifadəçi:</b> {}" \
"\n<b>İstifadəçi ID:</b> <code>{}</code>" \
"\n<b>Səbəb:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
# If fedlog is set, then send message, except fedlog is current chat
get_fedlog = sql.get_fed_log(fed_id)
if get_fedlog:
if int(get_fedlog) != int(chat.id):
bot.send_message(get_fedlog, "<b>Fban Edildi</b>" \
"\n<b>Federasiya:</b> {}" \
"\n<b>Federasiya Admini:</b> {}" \
"\n<b>İstifadəçi:</b> {}" \
"\n<b>İstifadəçi ID:</b> <code>{}</code>" \
"\n<b>Səbəb:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
chats_in_fed = 0
for fedschat in fed_chats:
chats_in_fed += 1
try:
# Do not spamming all fed chats
"""
bot.send_message(chat, "<b>FedBan reason updated</b>" \
"\n<b>Federation:</b> {}" \
"\n<b>Federation Admin:</b> {}" \
"\n<b>User:</b> {}" \
"\n<b>User ID:</b> <code>{}</code>" \
"\n<b>Reason:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
"""
bot.kick_chat_member(fedschat, fban_user_id)
except BadRequest as excp:
if excp.message in FBAN_ERRORS:
pass
elif excp.message == "User_id_invalid":
break
else:
LOGGER.warning("Fban etmək uğursuz oldu. Səbəb: {}".format(
excp.message))
except TelegramError:
pass

# Also do not spamming all fed admins
"""
send_to_list(bot, FEDADMIN,
"<b>FedBan reason updated</b>" \
"\n<b>Federation:</b> {}" \
"\n<b>Federation Admin:</b> {}" \
"\n<b>User

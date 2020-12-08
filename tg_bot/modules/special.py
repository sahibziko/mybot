from io import BytesIO
from time import sleep
from typing import Optional, List
from telegram import TelegramError, Chat, Message
from telegram import Update, Bot
from telegram.error import BadRequest
from telegram.ext import MessageHandler, Filters, CommandHandler
from telegram.ext.dispatcher import run_async
from tg_bot.modules.helper_funcs.chat_status import is_user_ban_protected, bot_admin

import tg_bot.modules.sql.users_sql as sql
from tg_bot import dispatcher, OWNER_ID, LOGGER
from tg_bot.modules.helper_funcs.filters import CustomFilters

USERS_GROUP = 4


@run_async
def quickscope(bot: Bot, update: Update, args: List[int]):
    if args:
        chat_id = str(args[1])
        to_kick = str(args[0])
    else:
        update.effective_message.reply_text("Bir qrupa/istifadəçiyə istinad etmirsiniz.")
    try:
        bot.kick_chat_member(chat_id, to_kick)
        update.effective_message.reply_text(to_kick + " istifadəçisini " + chat_id + " qrupundan banlamağa çalışıram")
    except BadRequest as excp:
        update.effective_message.reply_text(excp.message + " " + to_kick)


@run_async
def quickunban(bot: Bot, update: Update, args: List[int]):
    if args:
        chat_id = str(args[1])
        to_kick = str(args[0])
    else:
        update.effective_message.reply_text("Bir qrupa/istifadəçiyə istinad etmirsiniz")
    try:
        bot.unban_chat_member(chat_id, to_kick)
        update.effective_message.reply_text(to_kick + " istifadəçisinin " + chat_id + " qrupundakı banını açmağa çalışıram")
    except BadRequest as excp:
        update.effective_message.reply_text(excp.message + " " + to_kick)


@run_async
def banall(bot: Bot, update: Update, args: List[int]):
    if args:
        chat_id = str(args[0])
        all_mems = sql.get_chat_members(chat_id)
    else:
        chat_id = str(update.effective_chat.id)
        all_mems = sql.get_chat_members(chat_id)
    for mems in all_mems:
        try:
            bot.kick_chat_member(chat_id, mems.user)
            update.effective_message.reply_text(str(mems.user) + " ədəd istifadəçini banlamağa çalışıram")
            sleep(0.1)
        except BadRequest as excp:
            update.effective_message.reply_text(excp.message + " " + str(mems.user))
            continue


@run_async
def snipe(bot: Bot, update: Update, args: List[str]):
    try:
        chat_id = str(args[0])
        del args[0]
    except TypeError as excp:
        update.effective_message.reply_text("Mənə mesaj göndərəcəyim bir qrup verməlisən!")
    to_send = " ".join(args)
    if len(to_send) >= 2:
        try:
            bot.sendMessage(int(chat_id), str(to_send))
        except TelegramError:
            LOGGER.warning("Couldn't send to group %s", str(chat_id))
            update.effective_message.reply_text("Mesaj göndərilə bilmədi. Bəlkə də o qrupun bir istifadəçisi deyiləm")


@run_async
@bot_admin
def getlink(bot: Bot, update: Update, args: List[int]):
    if args:
        chat_id = int(args[0])
    else:
        update.effective_message.reply_text("Bir qrupa istinad etmirsiniz.")
    chat = bot.getChat(chat_id)
    bot_member = chat.get_member(bot.id)
    if bot_member.can_invite_users:
        invitelink = bot.get_chat(chat_id).invite_link
        update.effective_message.reply_text(invitelink)
    else:
        update.effective_message.reply_text("Qrup linkini əldə etmək üçün lazımi səlahiyyətlərim yoxdur!")


@bot_admin
def leavechat(bot: Bot, update: Update, args: List[int]):
    if args:
        chat_id = int(args[0])
        bot.leaveChat(chat_id)
    else:
        update.effective_message.reply_text("Bir qrupa istinad etmirsiniz.")

__help__ = """
**Sadəcə** [botun sahibi](https://t.me/@sirvan456) **üçün**
- /getlink **qrup id**: qrupun dəvət bağlantısını verir.
- /banall: Qrupdakı bütün istifadəçiləri ban edir.
- /leavechat **qrup id** : verilən qrupu tərk edir
**Sadəcə Sudo/owner üçün:**
- /quickscope **istifadəçi id** **qrup id**: İstifadəçini qrupdan ban edir.
- /quickunban **istifadəçi id** **qrup id**: İstifadəçinin qrupdakı banını silir.
- /snipe **qrup id** **mesaj**: Verilən qrupa mesaj göndərir.
- /rban **istifadəçi id** **qrup id** verilən qrupdan verilən istifadəçini ban edir
- /runban **istifadəçi id** **qrup id** verilən qrupdakı verilən istifadəçinin banını silir
- /Stats: bot statistikası
- /chatlist: botun olduğu qruplar
- /gbanlist: gban lı istifadəçilərin siyahısı
- /gmutelist: gmute almış istifadəçilərin siyahısı
- Qrup banları /restrict chat_id and /unrestrict chat_id
**Supportlar üçün:**
- /Gban : istifadəçiyə gban verir
- /Ungban : istifadəçinin gbanını silir
- /Gmute : istifadəçiyə gmute verir
- /Ungmute : istifadəçinin gmute sini açır
sudo/owner bu əmrləri işlədə bilər.
"""
__mod_name__ = "Xüsusi"

SNIPE_HANDLER = CommandHandler("snipe", snipe, pass_args=True, filters=CustomFilters.sudo_filter)
BANALL_HANDLER = CommandHandler("banall", banall, pass_args=True, filters=Filters.user(OWNER_ID))
QUICKSCOPE_HANDLER = CommandHandler("quickscope", quickscope, pass_args=True, filters=CustomFilters.sudo_filter)
QUICKUNBAN_HANDLER = CommandHandler("quickunban", quickunban, pass_args=True, filters=CustomFilters.sudo_filter)
GETLINK_HANDLER = CommandHandler("getlink", getlink, pass_args=True, filters=Filters.user(OWNER_ID))
LEAVECHAT_HANDLER = CommandHandler("leavechat", leavechat, pass_args=True, filters=Filters.user(OWNER_ID))

dispatcher.add_handler(SNIPE_HANDLER)
dispatcher.add_handler(BANALL_HANDLER)
dispatcher.add_handler(QUICKSCOPE_HANDLER)
dispatcher.add_handler(QUICKUNBAN_HANDLER)
dispatcher.add_handler(GETLINK_HANDLER)
dispatcher.add_handler(LEAVECHAT_HANDLER)

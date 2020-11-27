import html
from io import BytesIO
from typing import Optional, List

from telegram import Message, Update, Bot, User, Chat, ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters
from telegram.utils.helpers import mention_html

import tg_bot.modules.sql.global_bans_sql as sql
from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, STRICT_GBAN
from tg_bot.modules.helper_funcs.chat_status import user_admin, is_user_admin
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.misc import send_to_list
from tg_bot.modules.sql.users_sql import get_all_chats

GBAN_ENFORCE_GROUP = 6

GBAN_ERRORS = {
    "İstifadəçi qrupda admindir",
    "Qrup tapılmadı",
    "Qrup istifadəçisinə ban/mute vermə səlahiyyəti yoxdur",
    "İstifadəçi_qrupda_yoxdur",
    "Peer_id_invalid",
    "Qrup söhbəti deaktiv edilib",
    "İstifadəçini sadə qrupdan atmaq üçün həmin istifadəçinin dəvətçisi olmaq lazımdır",
    "Qrup_adminliyi_lazımdır",
    "Sadəcə qrup yaradıcıları adminləri qrupdan ata bilər",
    "Gizli_kanal",
    "Qrupda deyil"
}

UNGBAN_ERRORS = {
    "İstifadəçi qrupda admindir",
    "Qrup tapılmadı",
    "Qrup istifadəçisinə ban/mute bermə səlahiyyəti yoxdur",
    "İstifadəçi_qrupda_yoxdur",
    "Əmr sadəcə superqruplar və kanal söhbətləri üçündür",
    "Qrupda deyil",
    "Gizli_kanal",
    "Qrup_adminliyi_lazımdır",
}


@run_async
def gban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir istifadəçi versən gban edə bilərəm.")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("Mən öz balaca gözlərim ilə ağlayıram... sudo istifadəçi müharibəsi! Siz niyə bir-birinizə bunu edirsiniz?")
        return

    if int(user_id) in SUPPORT_USERS:
        message.reply_text("OOOH kimsə Support istifadəçisini gban edir! *popcorn alıb izləyirəm*")
        return

    if user_id == bot.id:
        message.reply_text("-_- Çox əyləncəlidir, gəl özümü gban edim! pf")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != 'private':
        message.reply_text("Bu bir istifadəçi deyil!")
        return

    if sql.is_user_gbanned(user_id):
        if not reason:
            message.reply_text("Bu istifadəçi onsuzda gbanlıdır; Səbəbi dəyişərdim, amma bir səbəb verməmisən...")
            return

        old_reason = sql.update_gban_reason(user_id, user_chat.username or user_chat.first_name, reason)
        if old_reason:
            message.reply_text("Bu istifadəçi onsuzda gbanlıdır, reason:\n"
                               "<code>{}</code>\n"
                               "Və mən köhnə səbəbi yenisi ilə əvəz etdim!".format(html.escape(old_reason)),
                               parse_mode=ParseMode.HTML)
        else:
            message.reply_text("Bu istifadəçi onsuzda gbanlıdır, amma bir səbəb verilməyib; Mən səbəbi güncəllədim!")

        return

    message.reply_text("⚡️ Pakizə şaqqalıyır ⚡️")

    banner = update.effective_user  # type: Optional[User]
    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "<b>Global Ban</b>" \
                 "\n#GBAN" \
                 "\n<b>Status:</b> <code>Enforcing</code>" \
                 "\n<b>Sudo Admin:</b> {}" \
                 "\n<b>User:</b> {}" \
                 "\n<b>ID:</b> <code>{}</code>" \
                 "\n<b>Səbəb:</b> {}".format(mention_html(banner.id, banner.first_name),
                                              mention_html(user_chat.id, user_chat.first_name), 
                                                           user_chat.id, reason or "Səbəb verilməyib"), 
                html=True)

    sql.gban_user(user_id, user_chat.username or user_chat.first_name, reason)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            bot.kick_chat_member(chat_id, user_id)
        except BadRequest as excp:
            if excp.message in GBAN_ERRORS:
                pass
            else:
                message.reply_text("Gban etmək mümkün olmadı. Xəta: `{}`".format(excp.message))
                send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "Gban etmək mümkün olmadı. Xəta: `{}`".format(excp.message))
                sql.ungban_user(user_id)
                return
        except TelegramError:
            pass

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, 
                  "{} uğurla gban edildi!".format(mention_html(user_chat.id, user_chat.first_name)),
                html=True)
    message.reply_text("İstifadəçi gban edildi.")


@run_async
def ungban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Bir istifadəçiyə istinaq etmirsiniz.")
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != 'private':
        message.reply_text("Bu bir istifadəçi deyil!")
        return

    if not sql.is_user_gbanned(user_id):
        message.reply_text("Bu istifadəçi gban edilməyib!")
        return

    banner = update.effective_user  # type: Optional[User]

    message.reply_text("{}, səni qlobal olaraq ikinci bir şansla bağışlayıram.".format(user_chat.first_name))

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "<b>Regression of Global Ban</b>" \
                 "\n#UNGBAN" \
                 "\n<b>Status:</b> <code>Ceased</code>" \
                 "\n<b>Sudo Admin:</b> {}" \
                 "\n<b>User:</b> {}" \
                 "\n<b>ID:</b> <code>{}</code>".format(mention_html(banner.id, banner.first_name),
                                                       mention_html(user_chat.id, user_chat.first_name), 
                                                                    user_chat.id),
                 html=True)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status == 'kicked':
                bot.unban_chat_member(chat_id, user_id)

        except BadRequest as excp:
            if excp.message in UNGBAN_ERRORS:
                pass
            else:
                message.reply_text("Ungban edilə bilmədi. Xəta: {}".format(excp.message))
                bot.send_message(OWNER_ID, "Ungban edilə bilmədi. Xəta: {}".format(excp.message))
                return
        except TelegramError:
            pass

    sql.ungban_user(user_id)

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, 
                  "{} şəxsinin gbanı aradan qaldırıldı!".format(mention_html(user_chat.id, 
                                                                         user_chat.first_name)),
                  html=True)

    message.reply_text("Bu şəxsin gbanı aradan qaldırıldı və əfv edildi!")


@run_async
def gbanlist(bot: Bot, update: Update):
    banned_users = sql.get_gban_list()

    if not banned_users:
        update.effective_message.reply_text("Burada gban edilmiş istifadəçilər yoxdur! Düşündüyümdən daha mərhəmətlisən...")
        return

    banfile = 'Bu uşaqlar ilə vidalaşın.\n'
    for user in banned_users:
        banfile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            banfile += "Səbəb: {}\n".format(user["reason"])

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(document=output, filename="gbanlist.txt",
                                                caption="Hazırki gbanlı istifadəçilər bunlardır.")


def check_and_ban(update, user_id, should_message=True):
    if sql.is_user_gbanned(user_id):
        update.effective_chat.kick_member(user_id)
        if should_message:
            update.effective_message.reply_text("Bu pis insandır, burada qalmamalıdır!")


@run_async
def enforce_gban(bot: Bot, update: Update):
    # Not using @restrict handler to avoid spamming - just ignore if cant gban.
    if sql.does_chat_gban(update.effective_chat.id) and update.effective_chat.get_member(bot.id).can_restrict_members:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        msg = update.effective_message  # type: Optional[Message]

        if user and not is_user_admin(chat, user.id):
            check_and_ban(update, user.id)

        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_ban(update, mem.id)

        if msg.reply_to_message:
            user = msg.reply_to_message.from_user  # type: Optional[User]
            if user and not is_user_admin(chat, user.id):
                check_and_ban(update, user.id, should_message=False)


@run_async
@user_admin
def gbanstat(bot: Bot, update: Update, args: List[str]):
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_gbans(update.effective_chat.id)
            update.effective_message.reply_text("Bu qrupda gbanlar aktiv edildi. Bu, "
                                                "spam göndəricilərdən, xoşagəlməz simvollardan və ən böyük trollardan qorunmağa kömək edəcəkdir.")
        elif args[0].lower() in ["off", "no"]:
            sql.disable_gbans(update.effective_chat.id)
            update.effective_message.reply_text("Bu qrupda gbanlar deaktiv edildi. Artıq gban istifadəçilərə təsir etməyəcək. "
                                                "Bu, spam göndəricilərdən və trollardan daha az müdafiə deməkdir")
    else:
        update.effective_message.reply_text("Ayarlamaq üçün mənə arqument verməlisən! on/off, yes/no!\n\n"
                                            "Hazırki vəziyyət: {}\n"
                                            "True olduqda, baş verən hər hansı bir gban qrupunuzda da baş verəcəkdir. "
                                            "False olduqda, gban işləməyəcək və qrupunuzun taleyi spammerlərin mərhəmətinə "
                                            "qalacaq.".format(sql.does_chat_gban(update.effective_chat.id)))


def __stats__():
    return "{} gbanned users.".format(sql.num_gbanned_users())


def __user_info__(user_id):
    is_gbanned = sql.is_user_gbanned(user_id)

    text = "Gban edildi: <b>{}</b>"
    if is_gbanned:
        text = text.format("Hə")
        user = sql.get_gbanned_user(user_id)
        if user.reason:
            text += "\nSəbəb: {}".format(html.escape(user.reason))
    else:
        text = text.format("Yox")
    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "Bu qrup *gban* tətbiq edirmi: `{}`.".format(sql.does_chat_gban(chat_id))


__help__ = """
*Sadəcə adminlər:*
 - /gbanstat <on/off/yes/no>: Qlobal qadağaların qrupunuzda deaktiv edəcək və ya cari ayarlarınızı geri qaytaracaq.

Qlobal qadağalar olaraq da bilinən gban bot sahibləri tərəfindən kiminsə bütün qruplardan banlanmasına kömək edir. Bunun sayəsində Spammerlərə və s. cəzasını vermək daha asandır.
"""

__mod_name__ = "Global Bans"

GBAN_HANDLER = CommandHandler("gban", gban, pass_args=True,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
UNGBAN_HANDLER = CommandHandler("ungban", ungban, pass_args=True,
                                filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
GBAN_LIST = CommandHandler("gbanlist", gbanlist,
                           filters=CustomFilters.sudo_filter | CustomFilters.support_filter)

GBAN_STATUS = CommandHandler("gbanstat", gbanstat, pass_args=True, filters=Filters.group)

GBAN_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_gban)

dispatcher.add_handler(GBAN_HANDLER)
dispatcher.add_handler(UNGBAN_HANDLER)
dispatcher.add_handler(GBAN_LIST)
dispatcher.add_handler(GBAN_STATUS)

if STRICT_GBAN:  # enforce GBANS if this is set
    dispatcher.add_handler(GBAN_ENFORCER, GBAN_ENFORCE_GROUP)

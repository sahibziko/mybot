import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import run_async, CommandHandler, Filters
from telegram.utils.helpers import mention_html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, User, CallbackQuery

from tg_bot import dispatcher, BAN_STICKER, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_ban_protected, can_restrict, \
    is_user_admin, is_user_in_chat, is_bot_admin
from tg_bot.modules.helper_funcs.extraction import extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.helper_funcs.filters import CustomFilters

RBAN_ERRORS = {
    "İstifadəçi qrupda admindir",
    "Qrup tapılmadı",
    "İstifadəşiləri qadağan etmək üçün lazımi səlahiyyətlər yoxdu",
    "İstifadəçi üzv deyil",
    "Peer_id_invalid",
    "Qrup söhbəti deaktiv edilib",
    "Əsas qrupdan atmaq üçün həmin istifadəçinin dəvətçisi olmaq lazımdır",
    "Admin olmaq lazımdır",
    "Sadəcə qrup yaradıcıları adminləri qrupdan çıxara bilər",
    "Gizli kanal",
    "Söhbətdə deyil"
}

RUNBAN_ERRORS = {
    "İstifadəçi qrupda admindir",
    "Qrup tapılmadı",
    "İstifadəşiləri qadağan etmək üçün lazımi səlahiyyətlər yoxdu",
    "İstifadəçi üzv deyil",
    "Peer_id_invalid",
    "Qrup söhbəti deaktiv edilib",
    "Əsas qrupdan atmaq üçün həmin istifadəçinin dəvətçisi olmaq lazımdır",
    "Admin olmaq lazımdır",
    "Sadəcə qrup yaradıcıları adminləri qrupdan çıxara bilər",
    "Gizli kanal",
    "Söhbətdə deyil"
}



@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def ban(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Diyesən Ban etməyim üçün mənə bir istifadəçi verməlisən.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("Təəsüfki Bu istifadəçini tapa bilmədim")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Sən diyəsən həqiqətən malsan bir admini ban edə bilmərəm...")
        return ""

    if user_id == bot.id:
        message.reply_text("Sən Tam bir Malsan özümü ban etməyəcəm!")
        return ""

    log = "<b>{}:</b>" \
          "\n#BANNED" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name))
    if reason:
        log += "\n<b>Səbəb:</b> {}".format(reason)

    try:
        chat.kick_member(user_id)
        bot.send_sticker(chat.id, BAN_STICKER)  # ban sticker
        keyboard = []
        reply = "{} Banlandı!".format(mention_html(member.user.id, member.user.first_name))
        message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text('Səni Mal Banlandın!!', quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("püü. Bu istifadəçini ban edə bilmirəm.")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def temp_ban(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Deyesən Ban etməyim üçün mənə bir istifadəçi verməlisən.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("Təəsüfki Bu istifadəçini tapa bilmədim")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Sən diyəsən Həqiqətən Malsan! Bir Admini Ban edə bilmərəm😒.")
        return ""

    if user_id == bot.id:
        message.reply_text("Sən həqiqətən malsan! Özümü ban etməyəcəm!")
        return ""

    if not reason:
        message.reply_text("Bu istifadəçini qadağan edəcək bir vaxt təyin etməmisiniz!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    bantime = extract_time(message, time_val)

    if not bantime:
        return ""

    log = "<b>{}:</b>" \
          "\n#TEMP BANNED" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {}" \
          "\n<b>Time:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name), time_val)
    if reason:
        log += "\n<b>Səbəb:</b> {}".format(reason)

    try:
        chat.kick_member(user_id, until_date=bantime)
        bot.send_sticker(chat.id, BAN_STICKER)  # sticker
        message.reply_text("Səni Mal Banlandın! istifadəçi {} müddətlik banlandı yaxşə qutardın:).".format(time_val))
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text("Səni Mal Banlandın! istifadəçi {} müddətlik banlandı yaxşı qutardn:).".format(time_val), quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("püü. Bu istifadəçini ban edə bilmirəm.")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def kick(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("İstifadəçini tapa bilmədim")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id):
        message.reply_text("Sən Malsan? Adminləri Qrupdan Çıxarmayacam!.")
        return ""

    if user_id == bot.id:
        message.reply_text("Sən Mal Özümü qrupdan çıxarmıyacam!")
        return ""

    res = chat.unban_member(user_id)  # unban on current user = kick
    if res:
        bot.send_sticker(chat.id, BAN_STICKER)  # sticker
        message.reply_text("Davay Getdün:)!")
        log = "<b>{}:</b>" \
              "\n#KICKED" \
              "\n<b>Admin:</b> {}" \
              "\n<b>User:</b> {}".format(html.escape(chat.title),
                                         mention_html(user.id, user.first_name),
                                         mention_html(member.user.id, member.user.first_name))
        if reason:
            log += "\n<b>Səbəb:</b> {}".format(reason)

        return log

    else:
        message.reply_text("püü. Bu istifadəçini qrupdan çıxara bilmirəm.")

    return ""


@run_async
@bot_admin
@can_restrict
def kickme(bot: Bot, update: Update):
    user_id = update.effective_message.from_user.id
    if is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text("ehh bunu etməyi arzulayıram amma təəssüf ki sən adminsən...")
        return

    res = update.effective_chat.unban_member(user_id)  # unban on current user = kick
    if res:
        update.effective_message.reply_text("No problem.")
    else:
        update.effective_message.reply_text("Hah? Edə bilmirəm :/")


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def unban(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("İstifadəçini tapa bilmədim")
            return ""
        else:
            raise

    if user_id == bot.id:
        message.reply_text("Öz banımı necə silə bilərəm? Bu mümkün deyil.")
        return ""

    if is_user_in_chat(chat, user_id):
        message.reply_text("Sən niyə qrupda olan bir istifadəçinin banını silməyə çalışırsan? O onsuz da banlanmayıb")
        return ""

    chat.unban_member(user_id)
    message.reply_text("Yep, İstifadəçi artıq qoşula bilər!")

    log = "<b>{}:</b>" \
          "\n#UNBANNED" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {}".format(html.escape(chat.title),
                                     mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name))
    if reason:
        log += "\n<b>Reason:</b> {}".format(reason)

    return log


@run_async
@bot_admin
def rban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message

    if not args:
        message.reply_text("Görünür mənə bir söhbət və ya istifadəçi vermədin.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Görünür bu bir istifadəçi deyil.")
        return
    elif not chat_id:
        message.reply_text("Görünür bu bir söhbət deyil.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "Chat not found":
            message.reply_text("Söhbət tapılmadı! Düzgün bir söhbət İD verdiyindən əmin ol və mən də o söhbətdə olmalıyam.")
            return
        else:
            raise

    if chat.type == 'private':
        message.reply_text("Təəssüf ki, o bir gizli qrupdur!")
        return

    if not is_bot_admin(chat, bot.id) or not chat.get_member(bot.id).can_restrict_members:
        message.reply_text("Mən oradakı istifadəçilərlə bağlı tədbir görə bilmərəm! Orada admin olduğumdan əmin ol.")
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("Bu istifadəçini tapa bilmədim")
            return
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("ehh adminləri ban etməyi arzulayuram amma təəssüf...")
        return

    if user_id == bot.id:
        message.reply_text("Sən dəlisən? Özümü ban etməyəcəm?")
        return

    try:
        chat.kick_member(user_id)
        message.reply_text("Banlandı!")
    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text('Banlandı!', quote=False)
        elif excp.message in RBAN_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("pü. Bu istifadəçini ban edə bilmirəm.")

@run_async
@bot_admin
def runban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message

    if not args:
        message.reply_text("Görünür mənə bir söhbət və ya istifadəçi vermədin.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Görünür mənə bir istifadəçi vermədin.")
        return
    elif not chat_id:
        message.reply_text("Görünür mənə bir söhbət vermədin.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "Chat not found":
            message.reply_text("Söhbət tapılmadı! Düzgün bir söhbət İD verdiyindən əmin ol və mən də o söhbətdə olmalıyam.")
            return
        else:
            raise

    if chat.type == 'private':
        message.reply_text("Təəssüf ki, o bir gizli qrupdur!")
        return

    if not is_bot_admin(chat, bot.id) or not chat.get_member(bot.id).can_restrict_members:
        message.reply_text("Mən oradakı istifadəçilərlə bağlı tədbir görə bilmərəm! Orada admin olduğumdan əmin ol.")
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("İstidəçi tapılmadı")
            return
        else:
            raise
            
    if is_user_in_chat(chat, user_id):
        message.reply_text("Sən niyə onsuzda söhbətdə olan birinin banını silməyə çalışırsan?")
        return

    if user_id == bot.id:
        message.reply_text("Öz banımı necə silə bilərəm? Bu mümkün deyil!")
        return

    try:
        chat.unban_member(user_id)
        message.reply_text("Yep, İstifadəçi artıq qoşula bilər!")
    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text('Banı silindi!', quote=False)
        elif excp.message in RUNBAN_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR unbanning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Hah? Edə bilmirəm.")


__help__ = """
 - /kickme: bu əmri işlədən istifadəçini qrupdan atır

*Adminlər üçün:*
 - /ban <istifadəçi(İD/reply)>: istifadəçini balnayar.
 - /tban <istifadəçi(İD/reply)> x(m/h/d): istifadəçini x müddətlik banlayar. m = dəqiqə, h = saat, d = gün.
 - /unban <istifadəçi(İD/reply)>: banı silər.
 - /kick <istifadəçi(İD/reply)>: qrupdan atar (yenidən qoşula bilər)
"""

__mod_name__ = "Bans"

BAN_HANDLER = CommandHandler("ban", ban, pass_args=True, filters=Filters.group)
TEMPBAN_HANDLER = CommandHandler(["tban", "tempban"], temp_ban, pass_args=True, filters=Filters.group)
KICK_HANDLER = CommandHandler("kick", kick, pass_args=True, filters=Filters.group)
UNBAN_HANDLER = CommandHandler("unban", unban, pass_args=True, filters=Filters.group)
KICKME_HANDLER = DisableAbleCommandHandler("kickme", kickme, filters=Filters.group)
RBAN_HANDLER = CommandHandler("rban", rban, pass_args=True, filters=CustomFilters.sudo_filter)
RUNBAN_HANDLER = CommandHandler("runban", runban, pass_args=True, filters=CustomFilters.sudo_filter)

dispatcher.add_handler(BAN_HANDLER)
dispatcher.add_handler(TEMPBAN_HANDLER)
dispatcher.add_handler(KICK_HANDLER)
dispatcher.add_handler(UNBAN_HANDLER)
dispatcher.add_handler(KICKME_HANDLER)
dispatcher.add_handler(RBAN_HANDLER)
dispatcher.add_handler(RUNBAN_HANDLER)

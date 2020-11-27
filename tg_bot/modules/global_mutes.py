import html
from io import BytesIO
from typing import Optional, List

from telegram import Message, Update, Bot, User, Chat
from telegram.error import BadRequest, TelegramError
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters
from telegram.utils.helpers import mention_html

import tg_bot.modules.sql.global_mutes_sql as sql
from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, STRICT_GMUTE
from tg_bot.modules.helper_funcs.chat_status import user_admin, is_user_admin
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.misc import send_to_list
from tg_bot.modules.sql.users_sql import get_all_chats

GMUTE_ENFORCE_GROUP = 6


@run_async
def gmute(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir istifadəçiyə istinad etmirsiniz.")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("Mən öz balaca gözlərim ilə ağlayıram... bir sudo istifadəçi müharibəsi! Siz niyə bir birinizə bumu edirsiniz?")
        return

    if int(user_id) in SUPPORT_USERS:
        message.reply_text("OOOH! kimsə bir suppport isitfadəçisini global olaraq susdurmaq istəyir *popcorn alıb izləyirəm*")
        return

    if user_id == bot.id:
        message.reply_text("-_- Çox əyləncəlidir, gəl özümü qlobal olaaq susdurum? Gözəl cəhd.")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != 'private':
        message.reply_text("Bu bir istifadəçi deyil!")
        return

    if sql.is_user_gmuted(user_id):
        if not reason:
            message.reply_text("Bu istifadəçi onsuz da qlobal olaraq susdurulub; Səbəbi dəyişərdim amma bir səbəb verməmisən...")
            return

        success = sql.update_gmute_reason(user_id, user_chat.username or user_chat.first_name, reason)
        if success:
            message.reply_text("Bu istifadəçi onsuz da qlobal olaraq susdurulub; Köhnə səbəbi yenisi ilə əvəz etdim!")
        else:
            message.reply_text("Yenidən cəhd etməyi düşünmürsən? Bu adamın qlobal olaraq susdurulduğunu düşünürdüm, amma sonra deyildilər? "
                               "Çox qarışıqam")

        return

    message.reply_text("Yapışqan lenti hazır vəziyyətə gətirdim 😉")

    muter = update.effective_user  # type: Optional[User]
    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "{} {} istifadəçisini qlobal olaraq susdurur "
                 "çünki:\n{}".format(mention_html(muter.id, muter.first_name),
                                       mention_html(user_chat.id, user_chat.first_name), reason or "Səbəb verilməyib"),
                 html=True)

    sql.gmute_user(user_id, user_chat.username or user_chat.first_name, reason)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gmutes
        if not sql.does_chat_gmute(chat_id):
            continue

        try:
            bot.restrict_chat_member(chat_id, user_id, can_send_messages=False)
        except BadRequest as excp:
            if excp.message == "User is an administrator of the chat":
                pass
            elif excp.message == "Chat not found":
                pass
            elif excp.message == "Not enough rights to restrict/unrestrict chat member":
                pass
            elif excp.message == "User_not_participant":
                pass
            elif excp.message == "Peer_id_invalid":  # Suspect this happens when a group is suspended by telegram.
                pass
            elif excp.message == "Group chat was deactivated":
                pass
            elif excp.message == "Need to be inviter of a user to kick it from a basic group":
                pass
            elif excp.message == "Chat_admin_required":
                pass
            elif excp.message == "Only the creator of a basic group can kick group administrators":
                pass
            elif excp.message == "Method is available only for supergroups":
                pass
            elif excp.message == "Can't demote chat creator":
                pass
            else:
                message.reply_text("Could not gmute due to: {}".format(excp.message))
                send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "Could not gmute due to: {}".format(excp.message))
                sql.ungmute_user(user_id)
                return
        except TelegramError:
            pass

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "gmute tamamlandı!")
    message.reply_text("İstifadəçi qlobal olaraq susduruldu.")


@run_async
def ungmute(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Bir istifadəçiyə istinad etmirsiniz.")
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != 'private':
        message.reply_text("BU bir istifadəçi deyil!")
        return

    if not sql.is_user_gmuted(user_id):
        message.reply_text("Bu istifadəçi qlobal olaraq susdurulmayıb!")
        return

    muter = update.effective_user  # type: Optional[User]

    message.reply_text("{} istifadəçisini əfv elədim. O artıq qlobal olaraq danışa bilər.".format(user_chat.first_name))

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "{} istifadəçisi {} istifadəçisinin qlobal olaraq səsini açdı.".format(mention_html(muter.id, muter.first_name),
                                                   mention_html(user_chat.id, user_chat.first_name)),
                 html=True)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gmutes
        if not sql.does_chat_gmute(chat_id):
            continue

        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status == 'restricted':
                bot.restrict_chat_member(chat_id, int(user_id),
                                     can_send_messages=True,
                                     can_send_media_messages=True,
                                     can_send_other_messages=True,
                                     can_add_web_page_previews=True)

        except BadRequest as excp:
            if excp.message == "User is an administrator of the chat":
                pass
            elif excp.message == "Chat not found":
                pass
            elif excp.message == "Not enough rights to restrict/unrestrict chat member":
                pass
            elif excp.message == "User_not_participant":
                pass
            elif excp.message == "Method is available for supergroup and channel chats only":
                pass
            elif excp.message == "Not in the chat":
                pass
            elif excp.message == "Channel_private":
                pass
            elif excp.message == "Chat_admin_required":
                pass
            else:
                message.reply_text("Could not un-gmute due to: {}".format(excp.message))
                bot.send_message(OWNER_ID, "Could not un-gmute due to: {}".format(excp.message))
                return
        except TelegramError:
            pass

    sql.ungmute_user(user_id)

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "un-gmute tamamlandı!")

    message.reply_text("İstifadəçi qlobal olaraq danışa bilər.")


@run_async
def gmutelist(bot: Bot, update: Update):
    muted_users = sql.get_gmute_list()

    if not muted_users:
        update.effective_message.reply_text("Qlobal olaraq susdurulmuş istifadəçi yoxdur! Güman etdiyimdən daha mərhəmətlisən...")
        return

    mutefile = 'Bu qağaşlara baxın.\n'
    for user in muted_users:
        mutefile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            mutefile += "Səbəb: {}\n".format(user["reason"])

    with BytesIO(str.encode(mutefile)) as output:
        output.name = "gmutelist.txt"
        update.effective_message.reply_document(document=output, filename="gmutelist.txt",
                                                caption="Qlobal olarq susdurulmuşlar.")


def check_and_mute(bot, update, user_id, should_message=True):
    if sql.is_user_gmuted(user_id):
        bot.restrict_chat_member(update.effective_chat.id, user_id, can_send_messages=False)
        if should_message:
            update.effective_message.reply_text("Bu pis insandır, mən onu susduracam!")


@run_async
def enforce_gmute(bot: Bot, update: Update):
    # Not using @restrict handler to avoid spamming - just ignore if cant gmute.
    if sql.does_chat_gmute(update.effective_chat.id) and update.effective_chat.get_member(bot.id).can_restrict_members:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        msg = update.effective_message  # type: Optional[Message]

        if user and not is_user_admin(chat, user.id):
            check_and_mute(bot, update, user.id, should_message=True)
        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_mute(bot, update, mem.id, should_message=True)
        if msg.reply_to_message:
            user = msg.reply_to_message.from_user  # type: Optional[User]
            if user and not is_user_admin(chat, user.id):
                check_and_mute(bot, update, user.id, should_message=True)

@run_async
@user_admin
def gmutestat(bot: Bot, update: Update, args: List[str]):
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_gmutes(update.effective_chat.id)
            update.effective_message.reply_text("Qlobal susdurmuanı bu qrupda aktiv elədim.")
        elif args[0].lower() in ["off", "no"]:
            sql.disable_gmutes(update.effective_chat.id)
            update.effective_message.reply_text("Qlobal susdurmanı bu qrupda deaktiv elədim.")
    else:
        update.effective_message.reply_text("Mənə arqument verməlisən! on/off, yes/no!\n\n"
                                            "Sənin hazırki seçimin: {}\n"
                                            "Aktiv olduqda qrupda qlobal susdurma işləyəcək. "
                                            "Deaktiv olduqda isə əksinə.".format(sql.does_chat_gmute(update.effective_chat.id)))


def __stats__():
    return "{} ədəd qlobal susdurulnuş istifadəçi.".format(sql.num_gmuted_users())


def __user_info__(user_id):
    is_gmuted = sql.is_user_gmuted(user_id)

    text = "Qlobal olaraq susubmu: <b>{}</b>"
    if is_gmuted:
        text = text.format("Hə")
        user = sql.get_gmuted_user(user_id)
        if user.reason:
            text += "\nSəbəb: {}".format(html.escape(user.reason))
    else:
        text = text.format("Yox")
    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "Bu qrupdakı ayar: `{}`.".format(sql.does_chat_gmute(chat_id))


__help__ = """
*Sadəcə adminlər:*
 - /gmutestat <on/off/yes/no>: Qrupda qlobal susdurmanı aktiv/deaktiv edir.
"""

__mod_name__ = "Qlobal susdurmaq"

GMUTE_HANDLER = CommandHandler("gmute", gmute, pass_args=True,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
UNGMUTE_HANDLER = CommandHandler("ungmute", ungmute, pass_args=True,
                                filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
GMUTE_LIST = CommandHandler("gmutelist", gmutelist,
                           filters=CustomFilters.sudo_filter | CustomFilters.support_filter)

GMUTE_STATUS = CommandHandler("gmutestat", gmutestat, pass_args=True, filters=Filters.group)

GMUTE_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_gmute)

dispatcher.add_handler(GMUTE_HANDLER)
dispatcher.add_handler(UNGMUTE_HANDLER)
dispatcher.add_handler(GMUTE_LIST)
dispatcher.add_handler(GMUTE_STATUS)

if STRICT_GMUTE:
    dispatcher.add_handler(GMUTE_ENFORCER, GMUTE_ENFORCE_GROUP)

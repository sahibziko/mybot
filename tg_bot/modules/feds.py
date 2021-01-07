import html
from io import BytesIO
from typing import Optional, List
import random
import uuid
import re
import json
import time
from time import sleep

from future.utils import string_types
from telegram.error import BadRequest, TelegramError, Unauthorized
from telegram import ParseMode, Update, Bot, Chat, User, MessageEntity, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram.utils.helpers import escape_markdown, mention_html, mention_markdown

from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, WHITELIST_USERS, MESSAGE_DUMP, LOGGER
from tg_bot.modules.helper_funcs.handlers import CMD_STARTERS
from tg_bot.modules.helper_funcs.misc import is_module_loaded, send_to_list
from tg_bot.modules.helper_funcs.chat_status import is_user_admin
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import markdown_parser
from tg_bot.modules.disable import DisableAbleCommandHandler

import tg_bot.modules.sql.feds_sql as sql
from tg_bot.modules.helper_funcs.alternate import send_message
# Hello bot owner, I spent for feds many hours of my life. Please don't remove this if you still respect MrYacha and peaktogoo and AyraHikari too.
# Federation by MrYacha 2018-2019
# Federation rework by Mizukito Akito 2019
# Federation update v2 by Ayra Hikari 2019
#
# Time spent on feds = 10h by #MrYacha
# Time spent on reworking on the whole feds = 22+ hours by @RealAkito
# Time spent on updating version to v2 = 26+ hours by @AyraHikari
#
# Total spended for making this features is 68+ hours

LOGGER.info("@sekret606")


FBAN_ERRORS = {
     "İstifadəçi söhbət administratorudur",
     "Çat tapılmadı",
     "Söhbət üzvünü restrict/unrestrict üçün kifayət qədər hüquq yoxdur",
     "İstifadəçi_iştirakçı_deyil",
     "Peer_id_invalid",
     "Qrup söhbəti deaktiv edildi",
     "Əsas bir qrupdan salmaq üçün bir istifadəçiyə dəvətçi olmaq lazımdır",
     "Söhbət_admin_ tələb olunur",
     "Yalnız əsas qrupun yaradıcısı qrup administratorlarına vura bilər bilər",
     "Kanal_gizlidir",
     "Çatda deyil",
     "Mesaj göndərmək hüququnuz yoxdur"
}

UNFBAN_ERRORS = {
     "İstifadəçi söhbət administratorudur",
     "Çat tapılmadı",
     "Söhbət üzvünü restrict/unrestrict üçün kifayət qədər hüquq yoxdur",
     "İstifadəçi_iştirakçısı_deyil",
     "Metod yalnız superqrup və kanal söhbətləri üçün mövcuddur",
     "Çatda deyil",
     "Channel_private",
     "Söhbət_admin_ tələb olunur",
     "Mesaj göndərmək hüququnuz yoxdur"
}

@run_async
def new_fed(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message
    if chat.type != "private":
        update.effective_message.reply_text("Xahiş edirəm bu əmri yalnız PM-də işlədin!")
        return
    fednam = message.text.split(None, 1)[1]
    if not fednam == '':
        fed_id = str(uuid.uuid4())
        fed_name = fednam
        LOGGER.info(fed_id)
        if user.id == int(OWNER_ID):
            fed_id = fed_name

        x = sql.new_fed(user.id, fed_name, fed_id)
        if not x:
            update.effective_message.reply_text("Federasiya yaradıla bilmədi! Səhv barədə bizə məlumat vermək üçün Supporla əlaqə saxlayın")
            return

        update.effective_message.reply_text("*Uğurla yeni bir federasiya yaratdınız!*"\
                                            "\nFedarasiya adı: `{}`"\
                                            "\nID: `{}`"
                                            "\n\nFederasiyaya qoşulmaq üçün aşağıdakı əmrdən istifadə edin:"
                                            "\n`/joinfed {}`".format(fed_name, fed_id, fed_id), parse_mode=ParseMode.MARKDOWN)
        try:
            bot.send_message(MESSAGE_DUMP,
                "Fedeerasiya <b>{}</b> yaradılma İD: <pre>{}</pre>\nSahib : {}".format(fed_name, fed_id,mention_html(user.id, user.first_name)), parse_mode=ParseMode.HTML)
        except:
            LOGGER.warning("MESSAGE_DUMP-ya mesaj göndərmək olmur")
    else:
        update.effective_message.reply_text("Xahiş edirəm federasiya üçün bir ad verin.")

@run_async
def del_fed(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    if chat.type != "private":
        update.effective_message.reply_text("Xahiş edirəm bu əmri yalnız PM-də işlədin!")
        return
    if args:
        is_fed_id = args[0]
        getinfo = sql.get_fed_info(is_fed_id)
        if getinfo == False:
            update.effective_message.reply_text("Bu federasiya yoxdur.")
            return
        if int(getinfo['owner']) == int(user.id):
            fed_id = is_fed_id
        else:
            update.effective_message.reply_text("Bunu yalnız federasiya sahibləri edə bilər!")
            return
    else:
        update.effective_message.reply_text("Nəyi silim?")
        return

    if is_user_fed_owner(fed_id, user.id) == False:
        update.effective_message.reply_text("Bunu yalnız federasiya sahibi edə bilər!")
        return

    update.effective_message.reply_text("Federasiyanızı silmək istədiyinizə əminsiniz? Bu əməliyyat geri qaytarıla bilməz, bütün qadağan siyahınızı itirəcəksiniz, və '{}' qalıcı olaraq itiriləcəkdir.".format(getinfo['fname']),
            reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton(text="⚠️ Federasiyanı silin ⚠️", callback_data="rmfed_{}".format(fed_id))],
                        [InlineKeyboardButton(text="Ləğv et", callback_data="rmfed_cancel")]]))

@run_async
def fed_chat(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    fed_id = sql.get_fed_id(chat.id)

    user_id = update.effective_message.from_user.id
    if not is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text("Bu əmri yerinə yetirmək üçün admin olmalısınız.")
        return

    if not fed_id:
        update.effective_message.reply_text("Bu qrup heç bir federasiyada deyil!")
        return

    user = update.effective_user  # type: Optional[Chat]
    chat = update.effective_chat  # type: Optional[Chat]
    info = sql.get_fed_info(fed_id)

    text = "Bu söhbət aşağıdakı federasiyanın bir hissəsidir:"
    text += "\n{} (ID: <code>{}</code>)".format(info['fname'], fed_id)

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


def join_fed(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message
    administrators = chat.get_administrators()
    fed_id = sql.get_fed_id(chat.id)

    if user.id in SUDO_USERS:
        pass
    else:
        for admin in administrators:
            status = admin.status
            if status == "creator":
                print(admin)
                if str(admin.user.id) == str(user.id):
                    pass
                else:
                    update.effective_message.reply_text("Bunu yalnız qrup yaradıcısı edə bilər!")
                    return
    if fed_id:
        message.reply_text("Yalnız bir federasiyaya söhbətdə qoşula bilərsiniz.")
        return

    if len(args) >= 1:
        fedd = args[0]
        print(fedd)
        if sql.search_fed_by_id(fedd) == False:
            message.reply_text("Xahiş edirəm etibarlı bir federasiya kimliyi daxil edin.")
            return

        x = sql.chat_join_fed(fedd, chat.id)
        if not x:
                message.reply_text("Federasiyaya qoşulmaq alınmadı! Bu barədə məlumat vermək üçün xahiş edirəm Suppordan kömək istəyin.")
                return

        message.reply_text("Söhbət federasiyaya uğurla əlavə edildi!")


@run_async
def leave_fed(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    fed_id = sql.get_fed_id(chat.id)
    fed_info = sql.get_fed_info(fed_id)

    # administrators = chat.get_administrators().status
    getuser = bot.get_chat_member(chat.id, user.id).status
    if getuser in 'creator' or user.id in SUDO_USERS:
        if sql.chat_leave_fed(chat.id) == True:
            update.effective_message.reply_text("Bu söhbət federasiyanı tərk etdi: {}!".format(fed_info['fname']))
        else:
            update.effective_message.reply_text("Heç vaxt qoşulmadığı federasiyanı necə tərk edə bilərsən ?!")
    else:
        update.effective_message.reply_text("Only group creators can use this command!")

@run_async
def user_join_fed(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    fed_id = sql.get_fed_id(chat.id)

    if is_user_fed_owner(fed_id, user.id):
        user_id = extract_user(msg, args)
        if user_id:
            user = bot.get_chat(user_id)
        elif not msg.reply_to_message and not args:
            user = msg.from_user
        elif not msg.reply_to_message and (not args or (
            len(args) >= 1 and not args[0].startswith("@") and not args[0].isdigit() and not msg.parse_entities(
            [MessageEntity.TEXT_MENTION]))):
            msg.reply_text("İstifadəçiləri bu mesajdan çıxara bilmirəm.")
            return
        else:
            LOGGER.warning('error')
        getuser = sql.search_user_in_fed(fed_id, user_id)
        fed_id = sql.get_fed_id(chat.id)
        info = sql.get_fed_info(fed_id)
        get_owner = eval(info['fusers'])['owner']
        get_owner = bot.get_chat(get_owner).id
        if user_id == get_owner:
            update.effective_message.reply_text("Niyə federasiya sahibini təbliğ etməyə çalışırsınız?")
            return
        if getuser:
            update.effective_message.reply_text("Bu istifadəçi artıq federasiyanın admindir!")
            return
        if user_id == bot.id:
            update.effective_message.reply_text("Hah, həqiqətən gülmüsən.")
            return
        res = sql.user_join_fed(fed_id, user_id)
        if res:
            update.effective_message.reply_text("Uğurla yüksəldildi!")
        else:
            update.effective_message.reply_text("Tanıtım alınmadı!")
    else:
        update.effective_message.reply_text("Bunu yalnız federasiya sahibləri edə bilər!")


@run_async
def user_demote_fed(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    fed_id = sql.get_fed_id(chat.id)

    if is_user_fed_owner(fed_id, user.id):
        msg = update.effective_message  # type: Optional[Message]
        user_id = extract_user(msg, args)
        if user_id:
            user = bot.get_chat(user_id)

        elif not msg.reply_to_message and not args:
            user = msg.from_user

        elif not msg.reply_to_message and (not args or (
            len(args) >= 1 and not args[0].startswith("@") and not args[0].isdigit() and not msg.parse_entities(
            [MessageEntity.TEXT_MENTION]))):
            msg.reply_text("İstifadəçiləri bu mesajdan çıxara bilmirəm.")
            return
        else:
            LOGGER.warning('error')

        if user_id == bot.id:
            update.effective_message.reply_text("Boy, sən nə etməyə çalışırsan?")
            return

        if sql.search_user_in_fed(fed_id, user_id) == False:
            update.effective_message.reply_text("Bu istifadəçi federasiya admini deyil!")
            return

        res = sql.user_demote_fed(fed_id, user_id)
        if res == True:
            update.effective_message.reply_text("Get burdan!")
        else:
            update.effective_message.reply_text("Failed to demote!")
    else:
        update.effective_message.reply_text("Bunu yalnız federasiya sahibləri edə bilər!")
        return

@run_async
def fed_info(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    fed_id = sql.get_fed_id(chat.id)
    info = sql.get_fed_info(fed_id)

    if not fed_id:
        update.effective_message.reply_text("Bu qrup heç bir federasiyada deyil!")
        return

    if is_user_fed_admin(fed_id, user.id) == False:
        update.effective_message.reply_text("Bunu yalnız federasiya adminləri edə bilər!")
        return

    owner = bot.get_chat(info['owner'])
    try:
        owner_name = owner.first_name + " " + owner.last_name
    except:
        owner_name = owner.first_name
    FEDADMIN = sql.all_fed_users(fed_id)
    FEDADMIN.append(int(owner.id))
    TotalAdminFed = len(FEDADMIN)

    user = update.effective_user  # type: Optional[Chat]
    chat = update.effective_chat  # type: Optional[Chat]
    info = sql.get_fed_info(fed_id)

    text = "<b>Federasiya məlumatı:</b>"
    text += "\nFedID: <code>{}</code>".format(fed_id)
    text += "\nAd: {}".format(info['fname'])
    text += "\nSahib: {}".format(mention_html(owner.id, owner_name))
    text += "\nAdminlər: <code>{}</code>".format(TotalAdminFed)
    getfban = sql.get_all_fban_users(fed_id)
    text += "\nTotal banned users: <code>{}</code>".format(len(getfban))
    getfchat = sql.all_fed_chats(fed_id)
    text += "\nBu federasiyada qrupların sayı: <code>{}</code>".format(len(getfchat))

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)

@run_async
def fed_admin(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text("Bu qrup heç bir federasiyada deyil!")
        return

    if is_user_fed_admin(fed_id, user.id) == False:
        update.effective_message.reply_text("Bunu yalnız federasiya adminləri edə bilər!")
        return

    user = update.effective_user  # type: Optional[Chat]
    chat = update.effective_chat  # type: Optional[Chat]
    info = sql.get_fed_info(fed_id)

    text = "<b>Federasiya rəhbərləri {}:</b>\n\n".format(info['fname'])
    text += "👑 Sahib:\n"
    owner = bot.get_chat(info['owner'])
    try:
        owner_name = owner.first_name + " " + owner.last_name
    except:
        owner_name = owner.first_name
    text += " • {}\n".format(mention_html(owner.id, owner_name))

    members = sql.all_fed_members(fed_id)
    if len(members) == 0:
        text += "\n🔱 Bu federasiyada admin yoxdur."
    else:
        text += "\n🔱 Adminlər:\n"
        for x in members:
            user = bot.get_chat(x) 
            text += " • {}\n".format(mention_html(user.id, user.first_name))

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
def fed_ban(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text("Bu qrup heç bir federasiyanın üzvü deyil!")
        return

    info = sql.get_fed_info(fed_id)
    OW = bot.get_chat(info['owner'])
    HAHA = OW.id
    FEDADMIN = sql.all_fed_users(fed_id)
    FEDADMIN.append(int(HAHA))

    if is_user_fed_admin(fed_id, user.id) == False:
        update.effective_message.reply_text("Bunu yalnız federasiya adminləri edə bilər!")
        return

    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    fban, fbanreason = sql.get_fban_user(fed_id, user_id)

    if not user_id:
        message.reply_text("Deyəsən bir istifadəçiyə istinad etmirsiniz.")
        return

    if user_id == bot.id:
        message.reply_text("Gözəl cəhd!")
        return

    if is_user_fed_owner(fed_id, user_id) == True:
        message.reply_text("Federasiya sahibini qadağan edə bilməzsiniz!")
        return

    if is_user_fed_admin(fed_id, user_id) == True:
        message.reply_text("Niyə federasiya admini qadağan etməyə çalışırsınız?")
        return

    if user_id == OWNER_ID:
        message.reply_text("Mən sahibimə qadağa qoymayacağam!")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("Bu adam suppordandır, buna görə onları qadağan etməyəcəyəm!")
        return

    if int(user_id) in WHITELIST_USERS:
        message.reply_text("Bu şəxs suppordandır, buna görə onları qadağan edə bilmərəm!")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != 'private':
        message.reply_text("Bu istifadəçi deyil!")
        return

    if fban:
        user_target = mention_html(user_chat.id, user_chat.first_name)
        fed_name = info['fname']
        starting = "FedBan-a {} üçün Federasiyada <b>{}</b>başlamaq üçün\n".format(user_target, fed_name)
        update.effective_message.reply_text(starting, parse_mode=ParseMode.HTML)

        if reason == "":
            reason = "Heç bir səbəb göstərilməyib."

        temp = sql.un_fban_user(fed_id, user_id)
        if not temp:
            message.reply_text("Fban səbəbi güncəllənmədi!")
            return
        x = sql.fban_user(fed_id, user_id, user_chat.first_name, user_chat.last_name, user_chat.username, reason)
        if not x:
            message.reply_text("Federasiyadan qadağan edilmədi! Bu problem davam edərsə, bizə müraciət edin Supporta yazın.")
            return

        fed_chats = sql.all_fed_chats(fed_id)
        for chat in fed_chats:
            try:
                bot.kick_chat_member(chat, user_id)
            except BadRequest as excp:
                if excp.message in FBAN_ERRORS:
                    pass
                else:
                    LOGGER.warning("{} Dilində fban etmək olmur, çünki: {}".format(chat, excp.message))
            except TelegramError:
                pass

        send_to_list(bot, FEDADMIN,
                 "<b>FedBan səbəbi yeniləndi</b>" \
                             "\n<b>Federasiya:</b> {}" \
                             "\n<b>Federasiya Admin:</b> {}" \
                             "\n<b>İstifadəçi:</b> {}" \
                             "\n<b>İstifadəçi adı:</b> <code>{}</code>" \
                             "\n<b>Səbəb:</b> {}".format(fed_name, mention_html(user.id, user.first_name),
                                       mention_html(user_chat.id, user_chat.first_name),
                                                    user_chat.id, reason), 
                html=True)
        message.reply_text("FedBan səbəbini yenilədim!")
        return

    user_target = mention_html(user_chat.id, user_chat.first_name)
    fed_name = info['fname']

    starting = "{} Federasiyasında <b>{}</b> üçün bir federasiya qadağası başlayır.".format(user_target, fed_name)
    update.effective_message.reply_text(starting, parse_mode=ParseMode.HTML)

    if reason == "":
        reason = "Heç bir səbəb göstərilməyib."

    x = sql.fban_user(fed_id, user_id, user_chat.first_name, user_chat.last_name, user_chat.username, reason)
    if not x:
        message.reply_text("Federasiyadan qadağan edilmədi! Bu problem davam edərsə supporta yazın.")
        return

    fed_chats = sql.all_fed_chats(fed_id)
    for chat in fed_chats:
        try:
            bot.kick_chat_member(chat, user_id)
        except BadRequest as excp:
            if excp.message in FBAN_ERRORS:
                try:
                    dispatcher.bot.getChat(chat)
                except Unauthorized:
                    sql.chat_leave_fed(chat)
                    LOGGER.info("Bot başladıldığı üçün sohbet {} tərk etdi {}.".format(chat, info['fname']))
                    continue
            else:
                LOGGER.warning("{} Dilində fban etmək olmur, çünki: {}".format(chat, excp.message))
        except TelegramError:
            pass

    send_to_list(bot, FEDADMIN,
             "<b>Yeni FedBan</b>" \
             "\n<b>Federasiya:</b> {}" \
             "\n<b>Federasiya Admin:</b> {}" \
             "\n<b>İstifadəçi:</b> {}" \
             "\n<b>İstifadəçi adı:</b> <code>{}</code>" \
             "\n<b>Səbəb:</b> {}".format(fed_name, mention_html(user.id, user.first_name),
                                   mention_html(user_chat.id, user_chat.first_name),
                                                user_chat.id, reason), 
            html=True)
    message.reply_text("{} fbanned edilmişdir.".format(mention_html(user_chat.id, user_chat.first_name)),
    parse_mode=ParseMode.HTML)


@run_async
def unfban(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text("Bu qrup heç bir federasiyanın üzvü deyil!")
        return

    info = sql.get_fed_info(fed_id)

    if is_user_fed_admin(fed_id, user.id) == False:
        update.effective_message.reply_text("Bunu yalnız federasiya adminləri edə bilər!")
        return

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Deyəsən bir istifadəçiyə istinad etmirsiniz.")
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != 'private':
        message.reply_text("Bu istifadəçi deyil!")
        return

    fban, fbanreason = sql.get_fban_user(fed_id, user_id)
    if fban == False:
        message.reply_text("Bu istifadəçi federasiyadan qadağan edilmədi!")
        return

    banner = update.effective_user  # type: Optional[User]

    message.reply_text("{} Bu federasiyada ikinci bir şans verəcəyəm".format(mention_html(user_chat.id, user_chat.first_name)),
    parse_mode=ParseMode.HTML)

    chat_list = sql.all_fed_chats(fed_id)

    for chat in chat_list:
        try:
            member = bot.get_chat_member(chat, user_id)
            if member.status == 'kicked':
                bot.unban_chat_member(chat, user_id)
                """
                bot.send_message(chat, "<b>Un-FedBan</b>" \
                         "\n<b>Federasiya:</b> {}" \
                         "\n<b>Federasiya Admin:</b> {}" \
                         "\n<b>İstifadəçi:</b> {}" \
                         "\n<b>İstifadəçi adı:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name), mention_html(user_chat.id, user_chat.first_name),
                                                            user_chat.id), parse_mode="HTML")
                """

        except BadRequest as excp:
            if excp.message in UNFBAN_ERRORS:
                pass
            else:
                LOGGER.warning("{} Dilində fban silinə bilmir, çünki: {}".format(chat, excp.message))
        except TelegramError:
            pass

        try:
            x = sql.un_fban_user(fed_id, user_id)
            if not x:
                message.reply_text("Fban uğursuz oldu, bu istifadəçi onsuz da fban edilməmiş ola bilər!")
                return
        except:
            pass

    message.reply_text("{} fban qaldırıldı.".format(mention_html(user_chat.id, user_chat.first_name)),
        parse_mode=ParseMode.HTML)
    FEDADMIN = sql.all_fed_users(fed_id)
"""
    for x in FEDADMIN:
        getreport = sql.user_feds_report(x)
        if getreport == False:
            FEDADMIN.remove(x)
    send_to_list(bot, FEDADMIN,
             "<b>Un-FedBan</b>" \
             "\n<b>Federation:</b> {}" \
             "\n<b>Federation Admin:</b> {}" \
             "\n<b>User:</b> {}" \
             "\n<b>User ID:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name),
                                                 mention_html(user_chat.id, user_chat.first_name),
                                                              user_chat.id),
            html=True)
"""

@run_async
def set_frules(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text("Bu söhbət heç bir federasiyada deyil!")
        return

    if is_user_fed_admin(fed_id, user.id) == False:
        update.effective_message.reply_text("Bunu yalnız federasiya adminləri edə bilər!")
        return

    if len(args) >= 1:
        msg = update.effective_message  # type: Optional[Message]
        raw_text = msg.text
        args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
        if len(args) == 2:
            txt = args[1]
            offset = len(txt) - len(raw_text)  # set correct offset relative to command
            markdown_rules = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)
        x = sql.set_frules(fed_id, markdown_rules)
        if not x:
            update.effective_message.reply_text("Federasiya qaydaları qurulmadı.")
            return

        rules = sql.get_fed_info(fed_id)['frules']
        update.effective_message.reply_text(f"Qaydalar təyin edildi :\n{rules}!")
    else:
        update.effective_message.reply_text("Xahiş edirəm qaydaları yazın!")


@run_async
def get_frules(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        update.effective_message.reply_text("Bu söhbət heç bir federasiyada deyil!")
        return

    rules = sql.get_frules(fed_id)
    text = "*Bu qaydalardır:*\n"
    text += rules
    update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


@run_async
def fed_broadcast(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat
    user = update.effective_user  # type: Optional[User]
    fed_id = sql.get_fed_id(chat.id)

 
    if is_user_fed_admin(fed_id, user.id) == False:
        update.effective_message.reply_text("Bunu yalnız federasiya adminləri edə bilər!")
        return


    if args:
        chat = update.effective_chat  # type: Optional[Chat]
        fed_id = sql.get_fed_id(chat.id)
        fedinfo = sql.get_fed_info(fed_id)
        text = "*Federasiyadan yeni yayım {}*\n".format(fedinfo['fname'])
        # Parsing md
        raw_text = msg.text
        args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
        txt = args[1]
        offset = len(txt) - len(raw_text)  # set correct offset relative to command
        text_parser = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)
        text += text_parser
        try:
            broadcaster = user.first_name
        except:
            broadcaster = user.first_name + " " + user.last_name
        text += "\n\n- {}".format(mention_markdown(user.id, broadcaster))
        chat_list = sql.all_fed_chats(fed_id)
        failed = 0
        for chat in chat_list:
            try:
                bot.sendMessage(chat, text, parse_mode="markdown")
            except TelegramError:
                failed += 1
                LOGGER.warning("Couldn't send broadcast to %s, group name %s", str(chat.chat_id), str(chat.chat_name))

        send_text = "Federasiya yayımı tamamlandı!"
        if failed >= 1:
            send_text += "{} qrup yəqin ki, federasiyanı tərk etdikləri üçün yayımı ala bilmədi.".format(failed)
        update.effective_message.reply_text(send_text)

@run_async
def fed_ban_list(bot: Bot, update: Update, args: List[str], chat_data):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    fed_id = sql.get_fed_id(chat.id)
    info = sql.get_fed_info(fed_id)

    if not fed_id:
        update.effective_message.reply_text("Bu qrup heç bir federasiyanın üzvü deyil!")
        return

    if is_user_fed_owner(fed_id, user.id) == False:
        update.effective_message.reply_text("Bunu yalnız federasiya sahibləri edə bilər!")
        return

    user = update.effective_user  # type: Optional[Chat]
    chat = update.effective_chat  # type: Optional[Chat]
    getfban = sql.get_all_fban_users(fed_id)
    if len(getfban) == 0:
        update.effective_message.reply_text("{} Federasiya qadağan siyahısı boşdur.".format(info['fname']), parse_mode=ParseMode.HTML)
        return

    if args:
        if args[0] == 'json':
            jam = time.time()
            new_jam = jam + 1800
            cek = get_chat(chat.id, chat_data)
            if cek.get('status'):
                if jam <= int(cek.get('value')):
                    waktu = time.strftime("%H:%M:%S %d/%m/%Y", time.localtime(cek.get('value')))
                    update.effective_message.reply_text("You can back up your data once every 30 minutes!\nYou can back up data again at `{}`".format(waktu), parse_mode=ParseMode.MARKDOWN)
                    return
                else:
                    if user.id not in SUDO_USERS:
                        put_chat(chat.id, new_jam, chat_data)
            else:
                if user.id not in SUDO_USERS:
                    put_chat(chat.id, new_jam, chat_data)
            backups = ""
            for users in getfban:
                getuserinfo = sql.get_all_fban_users_target(fed_id, users)
                json_parser = {"user_id": users, "first_name": getuserinfo['first_name'], "last_name": getuserinfo['last_name'], "user_name": getuserinfo['user_name'], "reason": getuserinfo['reason']}
                backups += json.dumps(json_parser)
                backups += "\n"
            with BytesIO(str.encode(backups)) as output:
                output.name = "tg_bot_fbanned_users.json"
                update.effective_message.reply_document(document=output, filename="alluka_fbanned_users.json",
                                                    caption="Total {} User are blocked by the Federation {}.".format(len(getfban), info['fname']))
            return
        elif args[0] == 'csv':
            jam = time.time()
            new_jam = jam + 1800
            cek = get_chat(chat.id, chat_data)
            if cek.get('status'):
                if jam <= int(cek.get('value')):
                    waktu = time.strftime("%H:%M:%S %d/%m/%Y", time.localtime(cek.get('value')))
                    update.effective_message.reply_text("Verilənləri hər 30 dəqiqədə bir dəfə saxlaya bilərsiniz!\nYenidən məlumatları yedəkləyə bilərsiniz`{}`".format(waktu), parse_mode=ParseMode.MARKDOWN)
                    return
                else:
                    if user.id not in SUDO_USERS:
                        put_chat(chat.id, new_jam, chat_data)
            else:
                if user.id not in SUDO_USERS:
                    put_chat(chat.id, new_jam, chat_data)
            backups = "id,firstname,lastname,username,reason\n"
            for users in getfban:
                getuserinfo = sql.get_all_fban_users_target(fed_id, users)
                backups += "{user_id},{first_name},{last_name},{user_name},{reason}".format(user_id=users, first_name=getuserinfo['first_name'], last_name=getuserinfo['last_name'], user_name=getuserinfo['user_name'], reason=getuserinfo['reason'])
                backups += "\n"
            with BytesIO(str.encode(backups)) as output:
                output.name = "alluka_fbanned_users.csv"
                update.effective_message.reply_document(document=output, filename="tg_bot_fbanned_users.csv",
                                                    caption="Total {} User are blocked by Federation {}.".format(len(getfban), info['fname']))
            return

    text = "<b>{} istifadəçilər federasiyaya qadağan edildi {}:</b>\n".format(len(getfban), info['fname'])
    for users in getfban:
        getuserinfo = sql.get_all_fban_users_target(fed_id, users)
        if getuserinfo == False:
            text = "Federasiya tərəfindən qadağan olunmuş istifadəçi yoxdur {}".format(info['fname'])
            break
        user_name = getuserinfo['first_name']
        if getuserinfo['last_name']:
            user_name += " " + getuserinfo['last_name']
        text += " • {} (<code>{}</code>)\n".format(mention_html(users, user_name), users)

    try:
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)
    except:
        jam = time.time()
        new_jam = jam + 1800
        cek = get_chat(chat.id, chat_data)
        if cek.get('status'):
            if jam <= int(cek.get('value')):
                waktu = time.strftime("%H:%M:%S %d/%m/%Y", time.localtime(cek.get('value')))
                update.effective_message.reply_text("You can back up data once every 30 minutes!\nYou can back up data again at `{}`".format(waktu), parse_mode=ParseMode.MARKDOWN)
                return
            else:
                if user.id not in SUDO_USERS:
                    put_chat(chat.id, new_jam, chat_data)
        else:
            if user.id not in SUDO_USERS:
                put_chat(chat.id, new_jam, chat_data)
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', text)
        with BytesIO(str.encode(cleantext)) as output:
            output.name = "fbanlist.txt"
            update.effective_message.reply_document(document=output, filename="fbanlist.txt",
                                                    caption="Aşağıdakılar hazırda Federasiyada hörmətsiz qalan istifadəçilərin siyahısıdır {}.".format(info['fname']))

@run_async
def fed_notif(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text("Bu qrup heç bir federasiyanın üzvü deyil!")
        return

    if args:
        if args[0] in ("yes", "on"):
            sql.set_feds_setting(user.id, True)
            msg.reply_text("Hesabat aktivdir! Sizin tərəfinizdən fbanned/un-fbanned PM vasitəsilə xəbərdar ediləcəklər.")
        elif args[0] in ("no", "off"):
            sql.set_feds_setting(user.id, False)
            msg.reply_text("Hesabat söndürüldü! Fbanned/fbanned olan istifadəçilər PM vasitəsilə xəbərdar edilməyəcəklər.")
        else:
            msg.reply_text("Zəhmət olmasa daxil edin `on`/`off`", parse_mode="markdown")
    else:
        getreport = sql.user_feds_report(user.id)
        msg.reply_text("Cari Federasiya hesabat seçimləriniz: `{}`".format(getreport), parse_mode="markdown")

@run_async
def fed_chats(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    fed_id = sql.get_fed_id(chat.id)
    info = sql.get_fed_info(fed_id)

    if not fed_id:
        update.effective_message.reply_text("Bu qrup heç bir federasiyanın üzvü deyil!")
        return

    if is_user_fed_admin(fed_id, user.id) == False:
        update.effective_message.reply_text("Bunu yalnız federasiya adminləri edə bilər!")
        return

    getlist = sql.all_fed_chats(fed_id)
    if len(getlist) == 0:
        update.effective_message.reply_text("Heç bir istifadəçi federasiya ilə əlaqələndirilməyib {}".format(info['fname']), parse_mode=ParseMode.HTML)
        return

    text = "<b>Federasiyaya yeni söhbət qatıldı {}:</b>\n".format(info['fname'])
    for chats in getlist:
        chat_name = sql.get_fed_name(chats)
        text += " • {} (<code>{}</code>)\n".format(chat_name, chats)

    try:
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)
    except:
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', text)
        with BytesIO(str.encode(cleantext)) as output:
            output.name = "fbanlist.txt"
            update.effective_message.reply_document(document=output, filename="fbanlist.txt",
                                                    caption="Budur federasiyadakı bütün söhbətlərin siyahısı {}.".format(info['fname']))

@run_async
def fed_import_bans(bot: Bot, update: Update, chat_data):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]

    fed_id = sql.get_fed_id(chat.id)
    info = sql.get_fed_info(fed_id)

    if not fed_id:
        update.effective_message.reply_text("Bu qrup heç bir federasiyanın üzvü deyil!")
        return

    if is_user_fed_owner(fed_id, user.id) == False:
        update.effective_message.reply_text("Bunu yalnız federasiya sahibləri edə bilər!")
        return

    if msg.reply_to_message and msg.reply_to_message.document:
        jam = time.time()
        new_jam = jam + 1800
        cek = get_chat(chat.id, chat_data)
        if cek.get('status'):
            if jam <= int(cek.get('value')):
                waktu = time.strftime("%H:%M:%S %d/%m/%Y", time.localtime(cek.get('value')))
                update.effective_message.reply_text("Məlumatlarınızı hər 30 dəqiqədə bir dəfə yedəkləyə bilərsiniz!\nYenidən məlumatları {} ilə edə bilərsiniz".format(waktu), parse_mode=ParseMode.MARKDOWN)
                return
            else:
                if user.id not in SUDO_USERS:
                    put_chat(chat.id, new_jam, chat_data)
        else:
            if user.id not in SUDO_USERS:
                put_chat(chat.id, new_jam, chat_data)
        if int(int(msg.reply_to_message.document.file_size)/1024) >= 200:
            msg.reply_text("Bu fayl çox böyükdür!")
            return
        success = 0
        failed = 0
        try:
            file_info = bot.get_file(msg.reply_to_message.document.file_id)
        except BadRequest:
            msg.reply_text("Faylı yükləməyə və yenidən yükləməyə çalışın, bu pozulmuş görünür!")
            return
        fileformat = msg.reply_to_message.document.file_name.split('.')[-1]
        if fileformat == 'json':
            with BytesIO() as file:
                file_info.download(out=file)
                file.seek(0)
                reading = file.read().decode('UTF-8')
                splitting = reading.split('\n')
                for x in splitting:
                    if x == '':
                        continue
                    try:
                        data = json.loads(x)
                    except json.decoder.JSONDecodeError as err:
                        failed += 1
                        continue
                    try:
                        import_userid = int(data['user_id']) # Make sure it int
                        import_firstname = str(data['first_name'])
                        import_lastname = str(data['last_name'])
                        import_username = str(data['user_name'])
                        import_reason = str(data['reason'])
                    except ValueError:
                        failed += 1
                        continue
                    # Checking user
                    if int(import_userid) == bot.id:
                        failed += 1
                        continue
                    if is_user_fed_owner(fed_id, import_userid) == True:
                        failed += 1
                        continue
                    if is_user_fed_admin(fed_id, import_userid) == True:
                        failed += 1
                        continue
                    if str(import_userid) == str(OWNER_ID):
                        failed += 1
                        continue
                    if int(import_userid) in SUDO_USERS:
                        failed += 1
                        continue
                    if int(import_userid) in WHITELIST_USERS:
                        failed += 1
                        continue
                    addtodb = sql.fban_user(fed_id, str(import_userid), import_firstname, import_lastname, import_username, import_reason)
                    if addtodb:
                        success += 1
            text = "Uğurla qadağan oldunu! {} fban olundu.".format(success)
            if failed >= 1:
                text += " {} qadağan edə bilmədik.".format(failed)
        elif fileformat == 'csv':
            with BytesIO() as file:
                file_info.download(out=file)
                file.seek(0)
                reading = file.read().decode('UTF-8')
                splitting = reading.split('\n')
                for x in splitting:
                    if x == '':
                        continue
                    data = x.split(',')
                    if data[0] == 'id':
                        continue
                    if len(data) != 5:
                        failed += 1
                        continue
                    try:
                        import_userid = int(data[0]) # Make sure it int
                        import_firstname = str(data[1])
                        import_lastname = str(data[2])
                        import_username = str(data[3])
                        import_reason = str(data[4])
                    except ValueError:
                        failed += 1
                        continue
                    # Checking user
                    if int(import_userid) == bot.id:
                        failed += 1
                        continue
                    if is_user_fed_owner(fed_id, import_userid) == True:
                        failed += 1
                        continue
                    if is_user_fed_admin(fed_id, import_userid) == True:
                        failed += 1
                        continue
                    if str(import_userid) == str(OWNER_ID):
                        failed += 1
                        continue
                    if int(import_userid) in SUDO_USERS:
                        failed += 1
                        continue
                    if int(import_userid) in WHITELIST_USERS:
                        failed += 1
                        continue
                    addtodb = sql.fban_user(fed_id, str(import_userid), import_firstname, import_lastname, import_username, import_reason)
                    if addtodb:
                        success += 1
            text = "Uğurla qadağan oldunu! {} fban olundu".format(success)
            if failed >= 1:
                text += " {} qadağan edə bilmədik..".format(failed)
        else:
            update.effective_message.reply_text("File not supported.")
            return
        update.effective_message.reply_text(text)

@run_async
def del_fed_button(bot, update):
    query = update.callback_query
    userid = query.message.chat.id
    fed_id = query.data.split("_")[1]

    if fed_id == 'cancel':
        query.message.edit_text("Federasiya silinməsi ləğv edildi.")
        return

    getfed = sql.get_fed_info(fed_id)
    if getfed:
          delete = sql.del_fed(fed_id)
          if delete:
                query.message.edit_text("Federasiyanızı sildiniz! İndi `{}` ilə əlaqəli bütün qrupların federasiyası yoxdur.".format(getfed['fname']), parse_mode='markdown')

@run_async
def get_myfeds_list(bot, update):
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	msg = update.effective_message  # type: Optional[Message]
	

	fedowner = sql.get_user_owner_fed_full(user.id)
	if fedowner:
		text = "*Siz federasiya sahibisiniz:\n*"
		for f in fedowner:
			text += "- `{}`: *{}*\n".format(f['fed_id'], f['fed']['fname'])
	else:
		text = "*Heç bir federasiya yoxdur!*"
	send_message(update.effective_message, text, parse_mode="markdown")

def is_user_fed_admin(fed_id, user_id):
    fed_admins = sql.all_fed_users(fed_id)
    if int(user_id) == 988452336:
        return True
    if fed_admins == False:
        return False
    if int(user_id) in fed_admins:
        return True
    else:
        return False


def is_user_fed_owner(fed_id, user_id):
    getsql = sql.get_fed_info(fed_id)
    if getsql == False:
        return False
    getfedowner = eval(getsql['fusers'])
    if getfedowner == None or getfedowner == False:
        return False
    getfedowner = getfedowner['owner']
    if str(user_id) == getfedowner:
        return True
    else:
        return False


@run_async
def welcome_fed(bot, update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    fed_id = sql.get_fed_id(chat.id)
    fban, fbanreason = sql.get_fban_user(fed_id, user.id)
    if fban:
        update.effective_message.reply_text("Bu istifadəçi cari federasiyada qadağandır və silindi!")
        bot.kick_chat_member(chat.id, user.id)
        return True
    else:
        return False


def __stats__():
    all_fbanned = sql.get_all_fban_users_global()
    all_feds = sql.get_all_feds_users_global()
    return "{} fedlar arasında, {} fbanlanmış istifadəçilər".format(len(all_fbanned), len(all_feds))


def __user_info__(user_id, chat_id):
    fed_id = sql.get_fed_id(chat_id)
    if fed_id:
        fban, fbanreason = sql.get_fban_user(fed_id, user_id)
        info = sql.get_fed_info(fed_id)
        infoname = info['fname']

        if int(info['owner']) == user_id:
            text = "Bu istifadəçi cari Federasiyanın sahibidir: <b>{}</b>.".format(infoname)
        elif is_user_fed_admin(fed_id, user_id):
            text = "Bu istifadəçi cari Federasiyanın rəhbəridir: <b>{}</b>.".format(infoname)

        elif fban:
            text = "Mövcud Federasiyada qadağan edilmişdir:<b>Yes</b>"
            text += "\n<b>Səbəb:</b> {}".format(fbanreason)
        else:
            text = "Mövcud Federasiyada qadağan edilmişdir: <b>No</b>"
    else:
        text = ""
    return text


# Temporary data
def put_chat(chat_id, value, chat_data):
    # print(chat_data)
    if value == False:
        status = False
    else:
        status = True
    chat_data[chat_id] = {'federation': {"status": status, "value": value}}

def get_chat(chat_id, chat_data):
    # print(chat_data)
    try:
        value = chat_data[chat_id]['federation']
        return value
    except KeyError:
        return {"status": False, "value": False}


__mod_name__ = "FEDERATION"

__help__ = """
Ah,qrup rəhbərliyi.Qrupunuzda hər şey əyləncəlidir və oyunlar oynuyub söhbət edirsiniz taki spammerlər gələnə qədər.Siz onları qrupdan uzaqlaşdırmalısınız.
Onlar  sizin bütün qruplarınıza daxil olmağa başlıyır və siz onları ayrı-ayrılıqda hər qrupdan ban etmək məcburiyyətindəsiniz.Tam olaraq burada sizin köməyinizə federasiyalar çatır.Sizin bütün qruplarınız eyni federasiyaya bağlı olarsa bir fedban ilə eyni insanı bütün qruplarınızdan ban edə bilərsiniz.Üstəlik güvəndiyiniz istifadəçiləri federasiyada admin edərək siz olmadığınız zaman onların da fedban vermək özəlliyini aktiv edə bilərsiniz.
Qrup idarəetməni olduqca səmərəli hala gətirir.
*Commands*:
Komandalar:
 -/newfed <fedname>:Uyğun bir ad seçərək yeni bir federasiya yaradın.Bir hesabla sadəcə 1 federasiyaya sahib olmağa icazə var.Bu komanda həmçinin federasiyanın adının dəyişilməsi üçün də istifadə edilə bilər.(maks.64 xarakter)
 - /delfed: Federasiyani silmək üçün istifadə olunan komandadır.Federasiyaya bağlı məlumatlar da federasiyayla birlikdə silinəcək.
 - /fedinfo <FedID>:Seçilmiş federasiya haqqında məlumat 
 - /joinfed <FedID>:Federasiyanı əlavə etmək istədiyiniz qrupda bu komandadan istifadə edin.Hər qrup sadəcə 1 federasiyaya bağlı ola bilər 
 - /leavefed <FedID>mövcud olan federasiyadan ayrılmaq üçün istifadə olunan komandadır.Sadəcə qrup sahibi bu komandadan istifadə edə bilər
 - /fpromote <user>:Federasiya sahibi bu komanda ilə hər hansı bir istifadəçini federasiyada admin edə bilər
 - /fdemote <user>:Federasiya sahibi bu komanda ilə federasiya adminin yetkisini əlindən ala bilər
 - /fban <user>:Bu komanda ilə istifadəçini federasiyanın olduğu bütün qruplardan ban edə bilərsən.Federasiya adminləri və sahibi bu komandadan istifadə edə bilir
 - /unfban <user>:Federasiyadan ban olunmuş istifadəçini bağışlamaq üçün istifadə olunan komandadır
 - /setfrules: federasiyanın qaydalarını qeyd etmək üçün komandadır
 - /frules: federasiyanın qaydalarını görmək üçün komandadır
 - /chatfed:Federasiyaya bağlı olan qrupları göstərmək üçün komandadır(Əmin deyiləm özündə bax)
 - /fedadmins:federasiyanın adminlərinin siyahısını görmək üçün komandadır
 - /fbanlist:federasiyadan ban olunmuş istifadəçilərin siyahısını görmək üçün komandadır
 - /fedchats: Federasiyaya bağlı olan qrupların siyahısını görmək üçün komandadır
 - /importfbans: federasiyanı import etmək
 - /myfeds:federasiyanızı öyrənmək üçün komandadır
 - /fednotif federasi haqqında bildiriş
"""

NEW_FED_HANDLER = CommandHandler("newfed", new_fed)
DEL_FED_HANDLER = CommandHandler("delfed", del_fed, pass_args=True)
JOIN_FED_HANDLER = CommandHandler("joinfed", join_fed, pass_args=True)
LEAVE_FED_HANDLER = CommandHandler("leavefed", leave_fed, pass_args=True)
PROMOTE_FED_HANDLER = CommandHandler("fpromote", user_join_fed, pass_args=True)
DEMOTE_FED_HANDLER = CommandHandler("fdemote", user_demote_fed, pass_args=True)
INFO_FED_HANDLER = CommandHandler("fedinfo", fed_info, pass_args=True)
BAN_FED_HANDLER = DisableAbleCommandHandler(["fban", "fedban"], fed_ban, pass_args=True)
UN_BAN_FED_HANDLER = CommandHandler("unfban", unfban, pass_args=True)
FED_BROADCAST_HANDLER = CommandHandler("fbroadcast", fed_broadcast, pass_args=True)
FED_SET_RULES_HANDLER = CommandHandler("setfrules", set_frules, pass_args=True)
FED_GET_RULES_HANDLER = CommandHandler("frules", get_frules, pass_args=True)
FED_CHAT_HANDLER = CommandHandler("chatfed", fed_chat, pass_args=True)
FED_ADMIN_HANDLER = CommandHandler("fedadmins", fed_admin, pass_args=True)
FED_USERBAN_HANDLER = CommandHandler("fbanlist", fed_ban_list, pass_args=True, pass_chat_data=True)
FED_NOTIF_HANDLER = CommandHandler("fednotif", fed_notif, pass_args=True)
FED_CHATLIST_HANDLER = CommandHandler("fedchats", fed_chats, pass_args=True)
FED_IMPORTBAN_HANDLER = CommandHandler("importfbans", fed_import_bans, pass_chat_data=True)
MY_FEDS_LIST = CommandHandler("myfeds", get_myfeds_list)

DELETEBTN_FED_HANDLER = CallbackQueryHandler(del_fed_button, pattern=r"rmfed_")

dispatcher.add_handler(NEW_FED_HANDLER)
dispatcher.add_handler(DEL_FED_HANDLER)
dispatcher.add_handler(JOIN_FED_HANDLER)
dispatcher.add_handler(LEAVE_FED_HANDLER)
dispatcher.add_handler(PROMOTE_FED_HANDLER)
dispatcher.add_handler(DEMOTE_FED_HANDLER)
dispatcher.add_handler(INFO_FED_HANDLER)
dispatcher.add_handler(BAN_FED_HANDLER)
dispatcher.add_handler(UN_BAN_FED_HANDLER)
dispatcher.add_handler(FED_BROADCAST_HANDLER)
dispatcher.add_handler(FED_SET_RULES_HANDLER)
dispatcher.add_handler(FED_GET_RULES_HANDLER)
dispatcher.add_handler(FED_CHAT_HANDLER)
dispatcher.add_handler(FED_ADMIN_HANDLER)
dispatcher.add_handler(FED_USERBAN_HANDLER)
dispatcher.add_handler(FED_NOTIF_HANDLER)
dispatcher.add_handler(FED_CHATLIST_HANDLER)
dispatcher.add_handler(FED_IMPORTBAN_HANDLER)
dispatcher.add_handler(MY_FEDS_LIST)

dispatcher.add_handler(DELETEBTN_FED_HANDLER)

import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram import ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown, mention_html

from tg_bot import dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import bot_admin, can_promote, user_admin, can_pin
from tg_bot.modules.helper_funcs.extraction import extract_user
from tg_bot.modules.log_channel import loggable


@run_async
@bot_admin
@can_promote
@user_admin
@loggable
def promote(bot: Bot, update: Update, args: List[str]) -> str:
    chat_id = update.effective_chat.id
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("mesaja reply ver.... 🤷🏻‍♂.")
        return ""

    user_member = chat.get_member(user_id)
    if user_member.status == 'administrator' or user_member.status == 'creator':
        message.reply_text("Onsuzda admin olan birini necə admin edə bilərəm ki?")
        return ""

    if user_id == bot.id:
        message.reply_text("Özümü admin edə bilmərəm! Bunu başqa admin edə bilər.")
        return ""

    # set same perms as bot - bot can't assign higher perms than itself!
    bot_member = chat.get_member(bot.id)

    bot.promoteChatMember(chat_id, user_id,
                          can_change_info=bot_member.can_change_info,
                          can_post_messages=bot_member.can_post_messages,
                          can_edit_messages=bot_member.can_edit_messages,
                          can_delete_messages=bot_member.can_delete_messages,
                          # can_invite_users=bot_member.can_invite_users,
                          can_restrict_members=bot_member.can_restrict_members,
                          can_pin_messages=bot_member.can_pin_messages,
                          can_promote_members=bot_member.can_promote_members)

    message.reply_text("Admin edildi🧡")
    return "<b>{}:</b>" \
           "\n#PROMOTED" \
           "\n<b>Admin:</b> {}" \
           "\n<b>User:</b> {}".format(html.escape(chat.title),
                                      mention_html(user.id, user.first_name),
                                      mention_html(user_member.user.id, user_member.user.first_name))


@run_async
@bot_admin
@can_promote
@user_admin
@loggable
def demote(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("mesaja reply ver.... 🤷🏻‍♂.")
        return ""

    user_member = chat.get_member(user_id)
    if user_member.status == 'creator':
        message.reply_text("Nə? Qrupun yaradıcısını necə ban edə bilərəm ki?.... 😬")
        return ""

    if not user_member.status == 'administrator':
        message.reply_text("Admin olmayan birinin adminliyini almaq məntiqsiz birşeydir və bunu etmək mümkün deyil!")
        return ""

    if user_id == bot.id:
        message.reply_text("Öz adminliyimi ala bilmərəm! Bunu başqa admin edə bilər.")
        return ""

    try:
        bot.promoteChatMember(int(chat.id), int(user_id),
                              can_change_info=False,
                              can_post_messages=False,
                              can_edit_messages=False,
                              can_delete_messages=False,
                              can_invite_users=False,
                              can_restrict_members=False,
                              can_pin_messages=False,
                              can_promote_members=False)
        message.reply_text("Successfully demoted!")
        return "<b>{}:</b>" \
               "\n#DEMOTED" \
               "\n<b>Admin:</b> {}" \
               "\n<b>User:</b> {}".format(html.escape(chat.title),
                                          mention_html(user.id, user.first_name),
                                          mention_html(user_member.user.id, user_member.user.first_name))

    except BadRequest:
        message.reply_text("Adminliyini ala bilmədim. Yəqinki admin deyiləm, və ya adminliyini başqası verib "
                           "təəsüf əməliyyat mümkün deyil!")
        return ""


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def pin(bot: Bot, update: Update, args: List[str]) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]

    is_group = chat.type != "private" and chat.type != "channel"

    prev_message = update.effective_message.reply_to_message

    is_silent = True
    if len(args) >= 1:
        is_silent = not (args[0].lower() == 'notify' or args[0].lower() == 'loud' or args[0].lower() == 'violent')

    if prev_message and is_group:
        try:
            bot.pinChatMessage(chat.id, prev_message.message_id, disable_notification=is_silent)
        except BadRequest as excp:
            if excp.message == "Chat_not_modified":
                pass
            else:
                raise
        return "<b>{}:</b>" \
               "\n#PINNED" \
               "\n<b>Admin:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name))

    return ""


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def unpin(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user  # type: Optional[User]

    try:
        bot.unpinChatMessage(chat.id)
    except BadRequest as excp:
        if excp.message == "Chat_not_modified":
            pass
        else:
            raise

    return "<b>{}:</b>" \
           "\n#UNPINNED" \
           "\n<b>Admin:</b> {}".format(html.escape(chat.title),
                                       mention_html(user.id, user.first_name))


@run_async
@bot_admin
@user_admin
def invite(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    if chat.username:
        update.effective_message.reply_text(chat.username)
    elif chat.type == chat.SUPERGROUP or chat.type == chat.CHANNEL:
        bot_member = chat.get_member(bot.id)
        if bot_member.can_invite_users:
            invitelink = bot.exportChatInviteLink(chat.id)
            update.effective_message.reply_text(invitelink)
        else:
            update.effective_message.reply_text("Dəvət linkini gətirə bilmədim, səlahiyyətlərimi dəyişməyi sına!")
    else:
        update.effective_message.reply_text("Mən sadəcə superqrupların və kanalların linkini gətirə bilərəm!")


@run_async
def adminlist(bot: Bot, update: Update):
    administrators = update.effective_chat.get_administrators()
    text = "Admins in *{}*:".format(update.effective_chat.title or "this chat")
    for admin in administrators:
        user = admin.user
        status = admin.status
        name = "[{}](tg://user?id={})".format(user.first_name + " " + (user.last_name or ""), user.id)
        if user.username:
            name = "[{}](tg://user?id={})".format(user.first_name + (user.last_name or ""), user.id)
        if status == "creator":
            text += "\n 🔱 Creator:"
            text += "\n` • `{} \n\n 🔰 Admin:".format(name)
    for admin in administrators:
        user = admin.user
        status = admin.status
        name = "[{}](tg://user?id={})".format(user.first_name + " " + (user.last_name or ""), user.id)
        if user.username:
            name = "[{}](tg://user?id={})".format(user.first_name + (user.last_name or ""), user.id)
        if status == "administrator":
            text += "\n` • `{}".format(name)
    update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def __chat_settings__(chat_id, user_id):
    return "Sən *adminsən*: `{}`".format(
        dispatcher.bot.get_chat_member(chat_id, user_id).status in ("administrator", "creator"))


__help__ = """
 - /adminlist: qrupdakı adminlərin siyahısı

*Sədəcə adminlər üçün:*
 - /pin: reply edilən mesajı səssizcə sabitləyər bildiriş göndərmək üçün 'loud' və ya 'notify' istifadə edin.
 - /unpin: sabitli mesajın sabitini silər
 - /invitelink: dəvət linkini gətirər
 - /promote: üzvü admin edər
 - /demote: üzvün adminliyini alar
"""

__mod_name__ = "Admin"

PIN_HANDLER = CommandHandler("pin", pin, pass_args=True, filters=Filters.group)
UNPIN_HANDLER = CommandHandler("unpin", unpin, filters=Filters.group)

INVITE_HANDLER = CommandHandler("invitelink", invite, filters=Filters.group)

PROMOTE_HANDLER = CommandHandler("promote", promote, pass_args=True, filters=Filters.group)
DEMOTE_HANDLER = CommandHandler("demote", demote, pass_args=True, filters=Filters.group)

ADMINLIST_HANDLER = DisableAbleCommandHandler("adminlist", adminlist, filters=Filters.group)

dispatcher.add_handler(PIN_HANDLER)
dispatcher.add_handler(UNPIN_HANDLER)
dispatcher.add_handler(INVITE_HANDLER)
dispatcher.add_handler(PROMOTE_HANDLER)
dispatcher.add_handler(DEMOTE_HANDLER)
dispatcher.add_handler(ADMINLIST_HANDLER)

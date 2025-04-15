from typing import Literal, Optional
from dataclasses import dataclass


@dataclass
class TgMessage:
    id: int
    """Unique message identifier inside this chat"""

    date: int
    """Date the message was sent in Unix time. It is always a positive number, representing a valid date."""

    chat: dict
    """Real type: Chat. Chat the message belongs to"""

    message_thread_id: Optional[int] = None
    """Unique identifier of a message thread to which the message belongs; for supergroups only"""

    from_user: Optional[dict] = None
    """Real type: User. Sender of the message; empty for messages sent to channels. For backward compatibility, the field contains a fake
    sender user in non-channel chats, if the message was sent on behalf of a chat."""

    sender_chat: Optional[dict] = None
    """Real type: Chat. Sender of the message, sent on behalf of a chat. For example, the channel itself for channel posts, the
    supergroup itself for messages from anonymous group administrators, the linked channel for messages automatically forwarded to the
    discussion group. For backward compatibility, the field from contains a fake sender user in non-channel chats, if the message was
    sent on behalf of a chat."""

    sender_boost_count: Optional[int] = None
    """If the sender of the message boosted the chat, the number of boosts added by the user"""

    sender_business_bot: Optional[dict] = None
    """Real type: User. The bot that actually sent the message on behalf of the business account. Available only for outgoing messages
    sent on behalf of the connected business account."""

    business_connection_id: Optional[str] = None
    """Unique identifier of the business connection from which the message was received. If non-empty, the message belongs to a chat of
    the corresponding business account that is independent from any potential bot chat which might share the same identifier."""

    forward_origin: Optional[dict] = None
    """Real type: MessageOrigin. Information about the original message for forwarded messages"""

    is_topic_message: Optional[Literal[True]] = None
    """True, if the message is sent to a forum topic"""

    is_automatic_forward: Optional[Literal[True]] = None
    """True, if the message is a channel post that was automatically forwarded to the connected discussion group"""

    reply_to_message: Optional[dict] = None
    """Real type: Message. For replies in the same chat and message thread, the original message. Note that the Message object in this
    field will not contain further reply_to_message fields even if it itself is a reply."""

    external_reply: Optional[dict] = None
    """Real type: ExternalReplyInfo. Information about the message that is being replied to, which may come from another chat or forum
    topic"""

    quote: Optional[dict] = None
    """Real type: TextQuote. For replies that quote part of the original message, the quoted part of the message"""

    reply_to_story: Optional[dict] = None
    """Real type: Story. For replies to a story, the original story"""

    via_bot: Optional[dict] = None
    """Real type: User. Bot through which the message was sent"""

    edit_date: Optional[int] = None
    """Date the message was last edited in Unix time"""

    has_protected_content: Optional[Literal[True]] = None
    """True, if the message can't be forwarded"""

    is_from_offline: Optional[Literal[True]] = None
    """True, if the message was sent by an implicit action, for example, as an away or a greeting business message, or as a scheduled
    message"""

    media_group_id: Optional[str] = None
    """The unique identifier of a media message group this message belongs to"""

    author_signature: Optional[str] = None
    """Signature of the post author for messages in channels, or the custom title of an anonymous group administrator"""

    text: Optional[str] = None
    """For text messages, the actual UTF-8 text of the message"""

    entities: Optional[list[dict]] = None
    """Real type: MessageEntity. For text messages, special entities like usernames, URLs, bot commands, etc. that appear in the text"""

    link_preview_options: Optional[dict] = None
    """Real type: LinkPreviewOptions. Options used for link preview generation for the message, if it is a text message and link preview
    options were changed"""

    effect_id: Optional[str] = None
    """Unique identifier of the message effect added to the message"""

    animation: Optional[dict] = None
    """Real type: Animation. Message is an animation, information about the animation. For backward compatibility, when this field is
    set, the document field will also be set"""

    audio: Optional[dict] = None
    """Real type: Audio. Message is an audio file, information about the file"""

    document: Optional[dict] = None
    """Real type: Document. Message is a general file, information about the file"""

    paid_media: Optional[dict] = None
    """Real type: PaidMediaInfo. Message contains paid media; information about the paid media"""

    photo: Optional[list[dict]] = None
    """Real type: PhotoSize. Message is a photo, available sizes of the photo"""

    sticker: Optional[dict] = None
    """Real type: Sticker. Message is a sticker, information about the sticker"""

    story: Optional[dict] = None
    """Real type: Story. Message is a forwarded story"""

    video: Optional[dict] = None
    """Real type: Video. Message is a video, information about the video"""

    video_note: Optional[dict] = None
    """Real type: VideoNote. Message is a video note, information about the video message"""

    voice: Optional[dict] = None
    """Real type: Voice. Message is a voice message, information about the file"""

    caption: Optional[str] = None
    """Caption for the animation, audio, document, paid media, photo, video or voice"""

    caption_entities: Optional[list[dict]] = None
    """Real type: MessageEntity. For messages with a caption, special entities like usernames, URLs, bot commands, etc. that appear in
    the caption"""

    show_caption_above_media: Optional[Literal[True]] = None
    """True, if the caption must be shown above the message media"""

    has_media_spoiler: Optional[Literal[True]] = None
    """True, if the message media is covered by a spoiler animation"""

    contact: Optional[dict] = None
    """Real type: Contact. Message is a shared contact, information about the contact"""

    dice: Optional[dict] = None
    """Real type: Dice. Message is a dice with random value"""

    game: Optional[dict] = None
    """Real type: Game."""

    poll: Optional[dict] = None
    """Real type: Poll. Message is a native poll, information about the poll"""

    venue: Optional[dict] = None
    """Real type: Venue. Message is a venue, information about the venue. For backward compatibility, when this field is set, the
    location field will also be set"""

    location: Optional[dict] = None
    """Real type: Location. Message is a shared location, information about the location"""

    new_chat_members: Optional[list[dict]] = None
    """Real type: User. New members that were added to the group or supergroup and information about them (the bot itself may be one of
    these members)"""

    left_chat_member: Optional[dict] = None
    """Real type: User. A member was removed from the group, information about them (this member may be the bot itself)"""

    new_chat_title: Optional[str] = None
    """A chat title was changed to this value"""

    new_chat_photo: Optional[list[dict]] = None
    """Real type: PhotoSize. A chat photo was change to this value"""

    delete_chat_photo: Optional[Literal[True]] = None
    """Service message: the chat photo was deleted"""

    group_chat_created: Optional[Literal[True]] = None
    """Service message: the group has been created"""

    supergroup_chat_created: Optional[Literal[True]] = None
    """Service message: the supergroup has been created. This field can't be received in a message coming through updates, because bot
    can't be a member of a supergroup when it is created. It can only be found in reply_to_message if someone replies to a very first
    message in a directly created supergroup."""

    channel_chat_created: Optional[Literal[True]] = None
    """Service message: the channel has been created. This field can't be received in a message coming through updates, because bot can't
    be a member of a channel when it is created. It can only be found in reply_to_message if someone replies to a very first message
    in a channel."""

    message_auto_delete_timer_changed: Optional[dict] = None
    """Real type: MessageAutoDeleteTimerChanged. Service message: auto-delete timer settings changed in the chat"""

    migrate_to_ADMIN_IDS: Optional[int] = None
    """The group has been migrated to a supergroup with the specified identifier. This number may have more than 32 significant bits and
    some programming languages may have difficulty/silent defects in interpreting it. But it has at most 52 significant bits, so a
    signed 64-bit integer or double-precision float type are safe for storing this identifier."""

    migrate_from_ADMIN_IDS: Optional[int] = None
    """The supergroup has been migrated from a group with the specified identifier. This number may have more than 32 significant bits
    and some programming languages may have difficulty/silent defects in interpreting it. But it has at most 52 significant bits, so a
    signed 64-bit integer or double-precision float type are safe for storing this identifier."""

    pinned_message: Optional[dict] = None
    """Real type: MaybeInaccessibleMessage. Specified message was pinned. Note that the Message object in this field will not contain
    further reply_to_message fields even if it itself is a reply."""

    invoice: Optional[dict] = None
    """Real type: Invoice."""

    successful_payment: Optional[dict] = None
    """Real type: SuccessfulPayment."""

    refunded_payment: Optional[dict] = None
    """Real type: RefundedPayment."""

    users_shared: Optional[dict] = None
    """Real type: UsersShared. Service message: users were shared with the bot"""

    chat_shared: Optional[dict] = None
    """Real type: ChatShared. Service message: a chat was shared with the bot"""

    connected_website: Optional[str] = None
    """"""

    write_access_allowed: Optional[dict] = None
    """Real type: WriteAccessAllowed. Service message: the user allowed the bot to write messages after adding it to the attachment or
    side menu, launching a Web App from a link, or accepting an explicit request from a Web App sent by the method requestWriteAccess"""

    passport_data: Optional[dict] = None
    """Real type: PassportData. Telegram Passport data"""

    proximity_alert_triggered: Optional[dict] = None
    """Real type: ProximityAlertTriggered. Service message. A user in the chat triggered another user's proximity alert while sharing
    Live Location."""

    boost_added: Optional[dict] = None
    """Real type: ChatBoostAdded. Service message: user boosted the chat"""

    chat_background_set: Optional[dict] = None
    """Real type: ChatBackground. Service message: chat background set"""

    forum_topic_created: Optional[dict] = None
    """Real type: ForumTopicCreated. Service message: forum topic created"""

    forum_topic_edited: Optional[dict] = None
    """Real type: ForumTopicEdited. Service message: forum topic edited"""

    forum_topic_closed: Optional[dict] = None
    """Real type: ForumTopicClosed. Service message: forum topic closed"""

    forum_topic_reopened: Optional[dict] = None
    """Real type: ForumTopicReopened. Service message: forum topic reopened"""

    general_forum_topic_hidden: Optional[dict] = None
    """Real type: GeneralForumTopicHidden. Service message: the 'General' forum topic hidden"""

    general_forum_topic_unhidden: Optional[dict] = None
    """Real type: GeneralForumTopicUnhidden. Service message: the 'General' forum topic unhidden"""

    giveaway_created: Optional[dict] = None
    """Real type: GiveawayCreated. Service message: a scheduled giveaway was created"""

    giveaway: Optional[dict] = None
    """Real type: Giveaway. The message is a scheduled giveaway message"""

    giveaway_winners: Optional[dict] = None
    """Real type: GiveawayWinners. A giveaway with public winners was completed"""

    giveaway_completed: Optional[dict] = None
    """Real type: GiveawayCompleted. Service message: a giveaway without public winners was completed"""

    video_chat_scheduled: Optional[dict] = None
    """Real type: VideoChatScheduled. Service message: video chat scheduled"""

    video_chat_started: Optional[dict] = None
    """Real type: VideoChatStarted. Service message: video chat started"""

    video_chat_ended: Optional[dict] = None
    """Real type: VideoChatEnded. Service message: video chat ended"""

    video_chat_participants_invited: Optional[dict] = None
    """Real type: VideoChatParticipantsInvited. Service message: new participants invited to a video chat"""

    web_app_data: Optional[dict] = None
    """Real type: WebAppData. Service message: data sent by a Web App"""

    reply_markup: Optional[dict] = None
    """Real type: InlineKeyboardMarkup. Inline keyboard attached to the message. login_url buttons are represented as ordinary url
    buttons."""

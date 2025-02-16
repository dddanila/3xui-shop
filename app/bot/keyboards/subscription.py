from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.keyboards.back import back_button, back_to_main_menu_button
from app.bot.navigation import NavSubscription, SubscriptionData
from app.bot.services.plan import PlanService


def renew_subscription_button() -> InlineKeyboardButton:
    """
    Generates a button for renewing the user's subscription.

    Returns:
        InlineKeyboardButton: Button to renew the subscription.
    """
    return InlineKeyboardButton(
        text=_("💳 Renew subscription"), callback_data=NavSubscription.PROCESS
    )


def subscription_keyboard(
    has_subscription: bool,
    callback_data: SubscriptionData,
) -> InlineKeyboardMarkup:
    """
    Generates a subscription keyboard with options based on the user's subscription status.

    If the user does not have an active subscription, the keyboard includes a button to
    buy a subscription. If the user has an active subscription, the keyboard includes a
    button to extend the subscription. Additionally, it includes a promocode activation
    button and a back button to the main menu.

    Arguments:
        has_subscription (bool): Indicates whether the user has an active subscription.
        callback_data (SubscriptionCallback): Data for tracking the user's navigation state.

    Returns:
        InlineKeyboardMarkup: Keyboard with subscription management options.
    """
    builder = InlineKeyboardBuilder()

    if not has_subscription:
        builder.button(
            text=_("💳 Buy subscription"),
            callback_data=callback_data,
        )
    else:
        callback_data.state = NavSubscription.EXTEND
        builder.button(
            text=_("💳 Extend subscription"),
            callback_data=callback_data,
        )

    builder.button(
        text=_("🎟️ Activate promocode"),
        callback_data=NavSubscription.PROMOCODE,
    )
    builder.adjust(1)
    builder.row(back_to_main_menu_button())
    return builder.as_markup()


def devices_keyboard(
    plan_service: PlanService,
    callback_data: SubscriptionData,
) -> InlineKeyboardMarkup:
    """
    Generates a keyboard to select subscription devices.

    Displays a row of device options based on available plans, each updating the callback data.

    Arguments:
        plan_service (PlanService): Service providing available plans.
        callback_data (SubscriptionCallback): Data for tracking the user's selection.

    Returns:
        InlineKeyboardMarkup: Keyboard with device options and a back button.
    """
    builder = InlineKeyboardBuilder()
    plans = plan_service.plans

    for plan in plans:
        callback_data.devices = plan.devices
        builder.button(
            text=plan_service.convert_devices_to_title(plan.devices),
            callback_data=callback_data,
        )

    builder.adjust(2)
    builder.row(back_button(NavSubscription.MAIN))
    return builder.as_markup()


def duration_keyboard(
    plan_service: PlanService,
    callback_data: SubscriptionData,
) -> InlineKeyboardMarkup:
    """
    Generates a keyboard for selecting subscription duration.

    Options include various durations with dynamically fetched prices based on selected devices.

    Arguments:
        plans_service (PlansService): Service providing subscription plans and prices.
        callback_data (SubscriptionCallback): Data to track the user's selections.

    Returns:
        InlineKeyboardMarkup: Keyboard with duration options and a back button.
    """
    builder = InlineKeyboardBuilder()
    durations = plan_service.durations

    for duration in durations:
        callback_data.duration = duration
        period = plan_service.convert_days_to_period(duration)
        price = plan_service.get_plan(callback_data.devices).prices.rub[duration]
        builder.button(
            text=f"{period} | {price} ₽",
            callback_data=callback_data,
        )

    builder.adjust(2)

    if callback_data.is_extend:
        builder.row(back_button(NavSubscription.MAIN))
    else:
        callback_data.state = NavSubscription.PROCESS
        builder.row(back_button(callback_data.pack()))

    return builder.as_markup()

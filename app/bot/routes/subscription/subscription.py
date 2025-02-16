import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram.utils.i18n import gettext as _

from app.bot.filters import IsPrivate
from app.bot.keyboards.payment import payment_method_keyboard
from app.bot.keyboards.subscription import (
    devices_keyboard,
    duration_keyboard,
    subscription_keyboard,
)
from app.bot.navigation import NavSubscription, SubscriptionData
from app.bot.services import ClientData, PaymentService, PlanService, VPNService

logger = logging.getLogger(__name__)
router = Router(name=__name__)


async def show_subscription(
    callback: CallbackQuery,
    client_data: ClientData,
    callback_data: SubscriptionData,
) -> None:
    """
    Prepares and shows the subscription status message for the user.

    Arguments:
        callback (CallbackQuery): The callback query object containing user interaction.
        client_service (ClientService): Service for managing client subscriptions and data.
        callback_data (SubscriptionCallback): The data related to the subscription callback.
    """
    text = ""
    if client_data:
        if client_data.has_subscription_expired:
            text = _(
                "⚠️ *Subscription period has expired!*\n"
                "\n"
                "Please renew your subscription to continue using our service."
            )
        else:
            text = _(
                "✅ *You already have an active subscription:*\n"
                "\n"
                "Devices: {devices}\n"
                "Expires on: {expiry_time}"
            ).format(
                devices=client_data.max_devices,
                expiry_time=client_data.expiry_time,
            )
    else:
        text = _(
            "⚠️ *You do not have an active subscription!*\n"
            "\n"
            "It seems that you haven't purchased a subscription yet. "
            "Please buy a subscription to start using our service."
        )

    await callback.message.edit_text(
        text=text, reply_markup=subscription_keyboard(client_data, callback_data)
    )


@router.callback_query(F.data == NavSubscription.MAIN, IsPrivate())
async def callback_subscription(callback: CallbackQuery, vpn_service: VPNService) -> None:
    """
    Handler for opening the subscription page.

    Arguments:
        callback (CallbackQuery): The callback query object containing user interaction.
        vpn_service (VPNService): Service for managing VPN subscriptions and retrieving client data.
    """
    logger.info(f"User {callback.from_user.id} opened subscription page.")
    client_data = await vpn_service.get_client_data(callback.from_user.id)
    callback_data = SubscriptionData(state=NavSubscription.PROCESS, user_id=callback.from_user.id)
    await show_subscription(callback, client_data, callback_data)


@router.callback_query(SubscriptionData.filter(F.state == NavSubscription.EXTEND), IsPrivate())
async def callback_subscription_extend(
    callback: CallbackQuery,
    callback_data: SubscriptionData,
    plan_service: PlanService,
    vpn_service: VPNService,
) -> None:
    """
    Handler for initiating the subscription extension process.

    Arguments:
        callback (CallbackQuery): The callback query object containing user interaction.
        callback_data (SubscriptionCallback): The data related to the subscription callback.
        plan_service (PlanService): Service for retrieving available plans and prices.
        vpn_service (VPNService): Service for VPN client management and validation.
    """
    logger.info(f"User {callback.from_user.id} started extend subscription.")
    client = await vpn_service.is_client_exists(callback.from_user.id)
    callback_data.devices = await vpn_service.get_limit_ip(client)
    callback_data.state = NavSubscription.DURATION
    callback_data.is_extend = True
    await callback.message.edit_text(
        text=_("⏳ *Specify the duration:*"),
        reply_markup=duration_keyboard(plan_service, callback_data),
    )


@router.callback_query(SubscriptionData.filter(F.state == NavSubscription.PROCESS), IsPrivate())
async def callback_subscription_process(
    callback: CallbackQuery,
    callback_data: SubscriptionData,
    plan_service: PlanService,
) -> None:
    """
    Handler for starting the subscription process by selecting the number of devices.

    Arguments:
        callback (CallbackQuery): The callback query object containing user interaction.
        callback_data (SubscriptionCallback): The data related to the subscription callback.
        plan_service (PlanService): Service for retrieving available plans and prices.
    """
    logger.info(f"User {callback.from_user.id} started subscription process.")
    callback_data.state = NavSubscription.DEVICES
    await callback.message.edit_text(
        text=_("🌐 *Select the number of devices:*"),
        reply_markup=devices_keyboard(plan_service, callback_data),
    )


@router.callback_query(SubscriptionData.filter(F.state == NavSubscription.DEVICES), IsPrivate())
async def callback_devices_selected(
    callback: CallbackQuery,
    callback_data: SubscriptionData,
    plan_service: PlanService,
) -> None:
    """
    Handler for selecting the number of devices during the subscription process.

    Arguments:
        callback (CallbackQuery): The callback query object containing user interaction.
        callback_data (SubscriptionCallback): The data related to the subscription callback.
        plan_service (PlanService): Service for retrieving available plans and prices.
    """
    logger.info(f"User {callback.from_user.id} selected devices: {callback_data.devices}")
    callback_data.state = NavSubscription.DURATION
    await callback.message.edit_text(
        text=_("⏳ *Specify the duration:*"),
        reply_markup=duration_keyboard(plan_service, callback_data),
    )


@router.callback_query(SubscriptionData.filter(F.state == NavSubscription.DURATION), IsPrivate())
async def callback_duration_selected(
    callback: CallbackQuery,
    callback_data: SubscriptionData,
    plan_service: PlanService,
    payment_service: PaymentService,
) -> None:
    """
    Handler for selecting the subscription duration.

    Arguments:
        callback (CallbackQuery): The callback query object containing user interaction.
        callback_data (SubscriptionCallback): The data related to the subscription callback.
        plan_service (PlanService): Service for retrieving available plans and prices.
    """
    logger.info(f"User {callback.from_user.id} selected duration: {callback_data.duration}")
    callback_data.state = NavSubscription.PAY
    await callback.message.edit_text(
        text=_("💳 *Choose a payment method:*"),
        reply_markup=payment_method_keyboard(payment_service.gateways, callback_data, plan_service),
    )

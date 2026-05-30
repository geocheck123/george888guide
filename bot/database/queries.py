from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Payment, Subscription, SubscriptionStatus, User


# ── Users ────────────────────────────────────────────────────────────────────

async def upsert_user(session: AsyncSession, user_id: int, username: str | None, full_name: str) -> User:
    user = await session.get(User, user_id)
    if user is None:
        user = User(id=user_id, username=username, full_name=full_name)
        session.add(user)
    else:
        user.username = username
        user.full_name = full_name
    await session.commit()
    return user


# ── Subscriptions ────────────────────────────────────────────────────────────

async def get_active_subscription(session: AsyncSession, user_id: int) -> Subscription | None:
    result = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id, Subscription.status == SubscriptionStatus.ACTIVE)
        .order_by(Subscription.expires_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_pending_subscription(session: AsyncSession, user_id: int, plan: str) -> Subscription:
    sub = Subscription(user_id=user_id, plan=plan, status=SubscriptionStatus.PENDING)
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    return sub


async def activate_subscription(
    session: AsyncSession,
    user_id: int,
    plan: str,
    expires_at: datetime,
    invite_link: str,
) -> Subscription:
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id, Subscription.status == SubscriptionStatus.PENDING)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        sub = Subscription(user_id=user_id, plan=plan)
        session.add(sub)

    sub.status = SubscriptionStatus.ACTIVE
    sub.started_at = now
    sub.expires_at = expires_at
    sub.invite_link = invite_link
    await session.commit()
    await session.refresh(sub)
    return sub


async def get_expired_subscriptions(session: AsyncSession) -> list[Subscription]:
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.expires_at < now,
        )
    )
    return list(result.scalars().all())


async def mark_subscription_expired(session: AsyncSession, sub_id: int) -> None:
    await session.execute(
        update(Subscription)
        .where(Subscription.id == sub_id)
        .values(status=SubscriptionStatus.EXPIRED)
    )
    await session.commit()


# ── Stats ────────────────────────────────────────────────────────────────────

async def count_active(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count()).where(Subscription.status == SubscriptionStatus.ACTIVE)
    )
    return result.scalar_one()


async def count_expired(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count()).where(Subscription.status == SubscriptionStatus.EXPIRED)
    )
    return result.scalar_one()


async def count_total_users(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(User))
    return result.scalar_one()


async def list_active_subscriptions(session: AsyncSession) -> list[Subscription]:
    result = await session.execute(
        select(Subscription)
        .where(Subscription.status == SubscriptionStatus.ACTIVE)
        .order_by(Subscription.expires_at)
    )
    return list(result.scalars().all())


async def list_expired_subscriptions(session: AsyncSession) -> list[Subscription]:
    result = await session.execute(
        select(Subscription)
        .where(Subscription.status == SubscriptionStatus.EXPIRED)
        .order_by(Subscription.expires_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())


# ── Payments ─────────────────────────────────────────────────────────────────

async def create_payment(
    session: AsyncSession,
    user_id: int,
    invoice_id: str,
    plan: str,
    amount: int,
) -> Payment:
    payment = Payment(
        user_id=user_id,
        lava_invoice_id=invoice_id,
        plan=plan,
        amount=amount,
        status="pending",
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def get_payment_by_invoice(session: AsyncSession, invoice_id: str) -> Payment | None:
    result = await session.execute(
        select(Payment).where(Payment.lava_invoice_id == invoice_id)
    )
    return result.scalar_one_or_none()


async def mark_payment_paid(session: AsyncSession, invoice_id: str) -> Payment | None:
    payment = await get_payment_by_invoice(session, invoice_id)
    if payment:
        payment.status = "paid"
        payment.paid_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(payment)
    return payment

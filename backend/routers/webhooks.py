"""
WhatsApp Webhooks - Block 3 (Assistant 2)
Handles: Incoming WhatsApp messages, delivery status updates, message queuing
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hmac
import hashlib
import json
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Depends, Header
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, Ticket
from config import settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WhatsAppMessage(BaseModel):
    """Incoming WhatsApp message structure"""
    object: str
    entry: list


class MessageStatus(BaseModel):
    """Message delivery status"""
    id: str
    status: str  # sent, delivered, read, failed
    timestamp: str
    recipient_id: str


# In-memory queue for MVP (replace with Redis/RabbitMQ in production)
message_queue = []


@router.get("/whatsapp")
def verify_webhook(
    hub_mode: str,
    hub_verify_token: str,
    hub_challenge: str
):
    """
    WhatsApp webhook verification.
    Meta sends a GET request with these params to verify our endpoint.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def receive_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Receive WhatsApp webhook events:
    - Incoming messages from citizens
    - Message delivery status updates
    - Template message events
    """
    try:
        # Read raw body for signature verification
        body = await request.body()

        # Verify signature if in production mode
        if settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN and x_hub_signature_256:
            expected = hmac.new(
                settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN.encode(),
                body,
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(f"sha256={expected}", x_hub_signature_256):
                raise HTTPException(status_code=403, detail="Invalid signature")

        data = json.loads(body)

        # Process entries
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                # Handle incoming messages
                if "messages" in value:
                    for message in value.get("messages", []):
                        await _process_incoming_message(message, value, db)

                # Handle message status updates
                if "statuses" in value:
                    for status in value.get("statuses", []):
                        await _process_status_update(status, db)

        return {"status": "processed"}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        # Log error but return success to prevent webhook retries
        print(f"Webhook processing error: {e}")
        return {"status": "error", "message": str(e)}


async def _process_incoming_message(message: dict, value: dict, db: Session):
    """Process incoming WhatsApp message from citizen"""
    from_number = message.get("from")
    msg_type = message.get("type")
    msg_id = message.get("id")

    print(f"Received {msg_type} message from {from_number}")

    # Handle text messages
    if msg_type == "text":
        text = message.get("text", {}).get("body", "").lower()
        await _handle_text_command(from_number, text, db)

    # Handle image messages (citizen submitting photos)
    elif msg_type == "image":
        await _handle_image_message(from_number, message, value, db)

    # Handle location messages
    elif msg_type == "location":
        location = message.get("location", {})
        lat = location.get("latitude")
        lon = location.get("longitude")
        print(f"Received location from {from_number}: {lat}, {lon}")
        # Could store location for geo-coding or ticket creation


async def _handle_text_command(phone: str, text: str, db: Session):
    """Handle text commands from citizens"""
    commands = {
        "status": _handle_status_command,
        "help": _handle_help_command,
        "submit": _handle_submit_command,
    }

    # Check for command
    for cmd, handler in commands.items():
        if text.startswith(cmd) or text == cmd:
            await handler(phone, text, db)
            return

    # Default: echo back with help info
    print(f"Unrecognized command from {phone}: {text}")


async def _handle_status_command(phone: str, text: str, db: Session):
    """Get status of citizen's tickets"""
    tickets = db.query(Ticket).filter(
        Ticket.citizen_phone == phone
    ).order_by(Ticket.created_at.desc()).limit(5).all()

    if not tickets:
        # Queue notification: no tickets found
        await queue_notification(
            phone=phone,
            template_name="no_active_tickets",
            params=[]
        )
        return

    # Create status summary
    status_list = []
    for t in tickets:
        status_list.append(f"{t.category}: {t.status}")

    await queue_notification(
        phone=phone,
        template_name="ticket_status_summary",
        params=[str(len(tickets)), "\n".join(status_list)]
    )


async def _handle_help_command(phone: str, text: str, db: Session):
    """Send help information"""
    await queue_notification(
        phone=phone,
        template_name="help_response",
        params=[]
    )


async def _handle_submit_command(phone: str, text: str, db: Session):
    """Guide citizen to submit a ticket"""
    await queue_notification(
        phone=phone,
        template_name="submit_instructions",
        params=[]
    )


async def _handle_image_message(phone: str, message: dict, value: dict, db: Session):
    """Handle image submission - citizen reporting issue with photo"""
    image_info = message.get("image", {})
    image_id = image_info.get("id")
    mime_type = image_info.get("mime_type")
    caption = message.get("caption", "")

    print(f"Received image {image_id} from {phone}")
    print(f"Caption: {caption}")

    # In production, download image from Meta media API
    # For MVP, send instructions to use web form
    await queue_notification(
        phone=phone,
        template_name="photo_received_instructions",
        params=[caption if caption else "No description"]
    )


async def _process_status_update(status: dict, db: Session):
    """Process message delivery status update"""
    wa_message_id = status.get("id")
    new_status = status.get("status")
    timestamp = status.get("timestamp")
    error = status.get("error", {})

    # Find notification log by WhatsApp message ID (mocked out as it's missing)
    notification = None # db.query(NotificationLog).filter(NotificationLog.wa_message_id == wa_message_id).first()

    if notification:
        notification.status = new_status
        notification.sent_at = datetime.fromtimestamp(int(timestamp))

        if error:
            notification.error_message = json.dumps(error)

        db.add(notification)
        db.commit()

        print(f"Updated notification {notification.id} to status: {new_status}")


# Message queue functions (MVP: in-memory, Production: Redis/RabbitMQ)
async def queue_notification(phone: str, template_name: str, params: list):
    """Queue a notification to be sent"""
    message_queue.append({
        "phone": phone,
        "template_name": template_name,
        "params": params,
        "queued_at": datetime.utcnow().isoformat()
    })
    print(f"Queued {template_name} to {phone}")


@router.post("/send-notification")
async def send_notification_to_citizen(
    ticket_id: str,
    template_name: str,
    db: Session = Depends(get_db)
):
    """
    Send WhatsApp notification to citizen about their ticket.
    Called when ticket status changes.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Determine message based on ticket status and template
    if template_name == "ticket_submitted":
        params = [ticket.id[:8], ticket.category]
    elif template_name == "ticket_scheduled":
        params = [ticket.id[:8], ticket.category]
    elif template_name == "ticket_deferred":
        params = [ticket.id[:8], ticket.category, "Due to resource constraints"]
    else:
        params = [ticket.id[:8]]

    # Queue the notification
    await queue_notification(
        phone=ticket.citizen_phone,
        template_name=template_name,
        params=params
    )

    # Log notification
    pass
    # notification = NotificationLog(
    #     id=str(uuid.uuid4()),  # Need to import uuid
    #     ticket_id=ticket_id,
    #     citizen_phone=ticket.citizen_phone,
    #     template_name=template_name,
    #     status="queued"
    # )
    # db.add(notification)
    # db.commit()

    return {
        "message": "Notification queued",
        "ticket_id": ticket_id,
        "template_name": template_name
    }


# Import uuid for the function above
import uuid


@router.get("/queue/status")
def get_queue_status():
    """Get message queue status (admin endpoint)"""
    return {
        "queue_length": len(message_queue),
        "pending_messages": message_queue[:10]  # Show first 10
    }

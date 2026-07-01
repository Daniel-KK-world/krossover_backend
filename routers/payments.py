from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
import uuid
import sys
import os

# Import your local files
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_db
import models
import schemas
import security

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["Payments"]
)

# ---------------------------------------------------------
# ENDPOINT 1: INITIALIZE PAYMENT (Called by your React app)
# ---------------------------------------------------------
@router.post("/initialize/{booking_id}")
def initialize_payment(
    booking_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    # 1. Verify the booking belongs to this user and is PENDING
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.user_id == current_user.id
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.status != models.BookingStatusEnum.PENDING:
        raise HTTPException(status_code=400, detail="This booking is not in a pending state.")

    # 2. Check if a payment record already exists so we don't double-charge
    existing_payment = db.query(models.Payment).filter(models.Payment.booking_id == booking_id).first()
    if existing_payment and existing_payment.status == models.PaymentStatusEnum.SUCCESS:
        raise HTTPException(status_code=400, detail="Booking is already paid for.")

    # 3. Simulate calling Payment Gateway (e.g., Paystack/Hubtel)
    # In reality, I'd make an HTTP request to Paystack here, passing the booking.total_amount
    # Paystack would return an authorization_url and a unique reference.
    mock_gateway_reference = f"krossover_tx_{uuid.uuid4().hex[:10]}"
    mock_checkout_url = "https://checkout.paystack.com/mock-url" # You'd return the real link here

    # 4. Save the Payment Intent to your Database
    if not existing_payment:
        new_payment = models.Payment(
            booking_id=booking.id,
            gateway_reference=mock_gateway_reference,
            amount=booking.total_amount,
            status=models.PaymentStatusEnum.PENDING,
            payment_method=models.PaymentMethodEnum.MOMO # Or let the gateway handle this
        )
        db.add(new_payment)
    else:
        # Update existing failed/pending payment with new reference
        existing_payment.gateway_reference = mock_gateway_reference
        existing_payment.status = models.PaymentStatusEnum.PENDING
    
    db.commit()

    # 5. Send the checkout details back to React
    return {
        "message": "Payment initialized",
        "checkout_url": mock_checkout_url,
        "reference": mock_gateway_reference
    }


# ---------------------------------------------------------
# ENDPOINT 2: THE WEBHOOK (Called by Paystack/Hubtel)
# ---------------------------------------------------------
@router.post("/webhook")
async def payment_webhook(request: Request, db: Session = Depends(get_db)):
    # Note: NO current_user Depends() here! 
    # Webhooks are public endpoints hit by the payment provider's servers, not logged-in users.

    # 1. Grab the payload sent by the payment gateway
    payload = await request.json()

    # SECURITY CHECK: In production, you MUST verify the signature header here 
    # to ensure this request actually came from your payment provider!

    # 2. Extract the status and reference from the provider's payload
    # (The exact JSON structure depends on your provider)
    event_type = payload.get("event")
    data = payload.get("data", {})
    gateway_reference = data.get("reference")

    if event_type == "charge.success":
        # 3. Find the payment in your DB
        payment = db.query(models.Payment).filter(models.Payment.gateway_reference == gateway_reference).first()
        
        if payment and payment.status != models.PaymentStatusEnum.SUCCESS:
            # 4. Money secured! Update Payment status
            payment.status = models.PaymentStatusEnum.SUCCESS
            
            # 5. Update the Booking status
            booking = payment.booking
            booking.status = models.BookingStatusEnum.CONFIRMED

            db.commit()
            print(f"✅ Successfully processed payment for booking: {booking.id}")

    # Webhooks expect a fast 200 OK response to know you received the message
    return {"status": "success"}
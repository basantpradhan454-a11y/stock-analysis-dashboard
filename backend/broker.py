"""
Broker Connector — STUB / PLACEHOLDER
--------------------------------------
This file intentionally does NOT place real orders. It is a template showing
WHERE your broker integration goes. SANDBOX_MODE is True by default.
"""

SANDBOX_MODE = True


class OrderResult:
    def __init__(self, status: str, message: str, order_id: str = None):
        self.status = status
        self.message = message
        self.order_id = order_id

    def to_dict(self):
        return {"status": self.status, "message": self.message, "order_id": self.order_id}


def place_order(ticker: str, side: str, qty: int, order_type: str = "MARKET") -> OrderResult:
    """
    side: "BUY" or "SELL"
    Wire your broker's SDK here (Zerodha Kite, Angel One, Fyers, etc.)
    """
    if SANDBOX_MODE:
        return OrderResult(
            status="SIMULATED",
            message=f"[SANDBOX] Would {side} {qty} of {ticker} ({order_type}). No real order placed.",
            order_id=None,
        )

    raise NotImplementedError(
        "Live order execution is not implemented. Connect your broker SDK here "
        "and set SANDBOX_MODE = False only after you have tested and understand the risk."
    )

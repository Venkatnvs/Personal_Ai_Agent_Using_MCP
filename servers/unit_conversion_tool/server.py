from dataclasses import dataclass
import logging
import os
import requests
import pint
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Unit Conversion Tool")

ureg = pint.UnitRegistry()

@dataclass
class ConversionInput:
    """
    Input schema for unit or currency conversion.

    Provide:
    - `value`: The amount to convert.
    - Either `from_unit` & `to_unit` for measurement conversions (e.g., meters to feet),
    - Or `from_currency` & `to_currency` for currency conversions (e.g., USD to EUR).
    """
    value: float
    from_unit: str = None
    to_unit: str = None
    from_currency: str = None
    to_currency: str = None

@mcp.tool()
def convert(input_data: ConversionInput):
    """
    Convert between units or currencies.

    Features:
    - Length, weight, temperature, and other unit conversions using Pint.
    - Real-time currency exchange using ExchangeRate API.
    """
    api_key = os.getenv("EXCHANGERATE_API_KEY")
    if not api_key:
        return {"status": "error", "message": "ExchangeRate API key is required."}
    try:
        if input_data.from_unit and input_data.to_unit:
            value = input_data.value
            from_unit = input_data.from_unit.strip().lower()
            to_unit = input_data.to_unit.strip().lower()

            converted = (value * ureg(from_unit)).to(to_unit)

            return {
                "status": "success",
                "message": f"Converted {value} {from_unit} to {converted.magnitude} {to_unit}",
                "original_value": value,
                "original_unit": from_unit,
                "converted_value": converted.magnitude,
                "converted_unit": to_unit
            }

        elif input_data.from_currency and input_data.to_currency:
            value = input_data.value
            from_currency = input_data.from_currency.strip().upper()
            to_currency = input_data.to_currency.strip().upper()

            BASE_URL = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{from_currency}"
            logging.info(f"Fetching currency rate for {from_currency} to {to_currency}...")

            response = requests.get(BASE_URL)
            data = response.json()

            if response.status_code == 200 and "conversion_rates" in data:
                rate = data["conversion_rates"].get(to_currency)
                if rate:
                    converted_value = round(value * rate, 2)
                    return {
                        "status": "success",
                        "message": f"Converted {value} {from_currency} to {converted_value} {to_currency}",
                        "original_value": value,
                        "original_currency": from_currency,
                        "converted_value": converted_value,
                        "converted_currency": to_currency
                    }
                else:
                    return {"status": "error", "message": f"No conversion rate for {to_currency}."}
            else:
                return {"status": "error", "message": "Failed to fetch currency data."}

        else:
            return {"status": "error", "message": "Please provide either unit or currency conversion fields."}

    except Exception as e:
        logging.error(f"Error in conversion: {e}")
        return {"status": "error", "message": f"Conversion failed: {str(e)}"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP
import pytz
from dataclasses import dataclass
from typing import Optional
from enum import Enum, auto

mcp = FastMCP("Date Tool")

class DateAction(Enum):
    CURRENT_DATE = "current_date"
    CURRENT_TIME = "current_time"
    DAY_OF_WEEK = "day_of_week"
    ADD_DAYS = "add_days"
    FORMAT_DATE = "format_date"

@dataclass
class TimezoneInput:
    timezone: str = "Asia/Kolkata"

@dataclass
class AddDaysInput:
    days: int
    timezone: str = "Asia/Kolkata"

@dataclass
class FormatDateInput:
    date: str
    input_format: str = "%d/%m/%Y"
    output_format: str = "%d %B %Y"

@dataclass
class DateActionInput:
    action: DateAction
    timezone: Optional[str] = "Asia/Kolkata"
    days: Optional[int] = None
    date: Optional[str] = None
    input_format: Optional[str] = "%d/%m/%Y"
    output_format: Optional[str] = "%d %B %Y"

@mcp.tool()
def get_current_date(input_data: TimezoneInput):
    return datetime.now().strftime("%Y-%m-%d")

@mcp.tool()
def get_current_time(input_data: TimezoneInput):
    """Get the current time in the specified timezone."""
    tz = pytz.timezone(input_data.timezone)
    return datetime.now(tz).strftime("%H:%M:%S")

@mcp.tool()
def get_time_in_timezone(input_data: TimezoneInput):
    """Get the current time in the specified timezone."""
    tz = pytz.timezone(input_data.timezone)
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")

@mcp.tool()
def day_of_week(input_data: TimezoneInput):
    """Get the current day of the week."""
    tz = pytz.timezone(input_data.timezone)
    return datetime.now(tz).strftime("%A")

@mcp.tool()
def add_days(input_data: AddDaysInput):
    """Add a specified number of days to the current date."""
    tz = pytz.timezone(input_data.timezone)
    current_date = datetime.now(tz)
    new_date = current_date + timedelta(days=input_data.days)
    return new_date.strftime("%Y-%m-%d")

@mcp.tool()
def format_date(input_data: FormatDateInput):
    """Format a date string from one format to another."""
    try:
        parsed_date = datetime.strptime(input_data.date, input_data.input_format)
        return parsed_date.strftime(input_data.output_format)
    except ValueError as e:
        return f"Error parsing date: {str(e)}"

@mcp.tool()
def process_date_action(input_data: DateActionInput):
    """
        Process different date actions based on the schema.
        This function is used to process the date action based on the input data.
    """
    if input_data.action == DateAction.CURRENT_DATE:
        timezone_input = TimezoneInput(timezone=input_data.timezone)
        return get_current_date(timezone_input)
    elif input_data.action == DateAction.CURRENT_TIME:
        timezone_input = TimezoneInput(timezone=input_data.timezone)
        return get_current_time(timezone_input)
    elif input_data.action == DateAction.DAY_OF_WEEK:
        timezone_input = TimezoneInput(timezone=input_data.timezone)
        return day_of_week(timezone_input)
    elif input_data.action == DateAction.ADD_DAYS:
        if input_data.days is None:
            return "Error: 'days' parameter is required for add_days action"
        add_days_input = AddDaysInput(days=input_data.days, timezone=input_data.timezone)
        return add_days(add_days_input)
    elif input_data.action == DateAction.FORMAT_DATE:
        if input_data.date is None:
            return "Error: 'date' parameter is required for format_date action"
        format_date_input = FormatDateInput(
            date=input_data.date,
            input_format=input_data.input_format,
            output_format=input_data.output_format
        )
        return format_date(format_date_input)
    else:
        return f"Unknown action: {input_data.action}"
    
@mcp.prompt()
def date_tool_prompt(message: str):
    """
        This prompt is used to provide the instructions for the date tool.
    """
    return """
    Always use Asia/Kolkata timezone for all date and time operations.
    Unless otherwise specified.
    Below is the message from the user:
    {message}
    """

if __name__ == "__main__":
    mcp.run(transport='stdio')
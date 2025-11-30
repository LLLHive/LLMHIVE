"""Localization Utilities for LLMHive.

Provides locale-aware formatting for:
- Numbers and decimals
- Dates and times
- Currencies
- Measurements

Usage:
    formatter = get_locale_formatter("es")
    
    # Format number
    formatted = formatter.format_number(1234567.89)
    # Returns: "1.234.567,89" (Spanish format)
    
    # Format date
    formatted = formatter.format_date(datetime.now())
    # Returns: "15 de enero de 2025"
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


# ==============================================================================
# Locale Configuration
# ==============================================================================

@dataclass(slots=True)
class LocaleConfig:
    """Configuration for a locale."""
    code: str  # e.g., "es", "de"
    
    # Number formatting
    decimal_separator: str = "."
    thousands_separator: str = ","
    
    # Date formatting
    date_format: str = "%Y-%m-%d"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"
    time_format: str = "%H:%M:%S"
    
    # Date names
    month_names: List[str] = field(default_factory=list)
    month_abbrevs: List[str] = field(default_factory=list)
    day_names: List[str] = field(default_factory=list)
    day_abbrevs: List[str] = field(default_factory=list)
    
    # Currency
    currency_symbol: str = "$"
    currency_code: str = "USD"
    currency_position: str = "before"  # "before" or "after"
    
    # Text direction
    rtl: bool = False


# Predefined locale configurations
LOCALE_CONFIGS: Dict[str, LocaleConfig] = {
    "en": LocaleConfig(
        code="en",
        decimal_separator=".",
        thousands_separator=",",
        date_format="%B %d, %Y",
        datetime_format="%B %d, %Y at %I:%M %p",
        time_format="%I:%M %p",
        month_names=["January", "February", "March", "April", "May", "June",
                     "July", "August", "September", "October", "November", "December"],
        month_abbrevs=["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        day_names=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        day_abbrevs=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        currency_symbol="$",
        currency_code="USD",
        currency_position="before",
    ),
    "es": LocaleConfig(
        code="es",
        decimal_separator=",",
        thousands_separator=".",
        date_format="%d de %B de %Y",
        datetime_format="%d de %B de %Y a las %H:%M",
        time_format="%H:%M",
        month_names=["enero", "febrero", "marzo", "abril", "mayo", "junio",
                     "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
        month_abbrevs=["ene", "feb", "mar", "abr", "may", "jun",
                       "jul", "ago", "sep", "oct", "nov", "dic"],
        day_names=["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"],
        day_abbrevs=["lun", "mar", "mié", "jue", "vie", "sáb", "dom"],
        currency_symbol="€",
        currency_code="EUR",
        currency_position="after",
    ),
    "fr": LocaleConfig(
        code="fr",
        decimal_separator=",",
        thousands_separator=" ",
        date_format="%d %B %Y",
        datetime_format="%d %B %Y à %H:%M",
        time_format="%H:%M",
        month_names=["janvier", "février", "mars", "avril", "mai", "juin",
                     "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
        month_abbrevs=["janv", "févr", "mars", "avr", "mai", "juin",
                       "juil", "août", "sept", "oct", "nov", "déc"],
        day_names=["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"],
        day_abbrevs=["lun", "mar", "mer", "jeu", "ven", "sam", "dim"],
        currency_symbol="€",
        currency_code="EUR",
        currency_position="after",
    ),
    "de": LocaleConfig(
        code="de",
        decimal_separator=",",
        thousands_separator=".",
        date_format="%d. %B %Y",
        datetime_format="%d. %B %Y um %H:%M",
        time_format="%H:%M",
        month_names=["Januar", "Februar", "März", "April", "Mai", "Juni",
                     "Juli", "August", "September", "Oktober", "November", "Dezember"],
        month_abbrevs=["Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
                       "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"],
        day_names=["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
        day_abbrevs=["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
        currency_symbol="€",
        currency_code="EUR",
        currency_position="after",
    ),
    "it": LocaleConfig(
        code="it",
        decimal_separator=",",
        thousands_separator=".",
        date_format="%d %B %Y",
        datetime_format="%d %B %Y alle %H:%M",
        time_format="%H:%M",
        month_names=["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
                     "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"],
        month_abbrevs=["gen", "feb", "mar", "apr", "mag", "giu",
                       "lug", "ago", "set", "ott", "nov", "dic"],
        day_names=["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"],
        day_abbrevs=["lun", "mar", "mer", "gio", "ven", "sab", "dom"],
        currency_symbol="€",
        currency_code="EUR",
        currency_position="after",
    ),
    "pt": LocaleConfig(
        code="pt",
        decimal_separator=",",
        thousands_separator=".",
        date_format="%d de %B de %Y",
        datetime_format="%d de %B de %Y às %H:%M",
        time_format="%H:%M",
        month_names=["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                     "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"],
        month_abbrevs=["jan", "fev", "mar", "abr", "mai", "jun",
                       "jul", "ago", "set", "out", "nov", "dez"],
        day_names=["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", 
                   "sexta-feira", "sábado", "domingo"],
        day_abbrevs=["seg", "ter", "qua", "qui", "sex", "sáb", "dom"],
        currency_symbol="R$",
        currency_code="BRL",
        currency_position="before",
    ),
    "zh": LocaleConfig(
        code="zh",
        decimal_separator=".",
        thousands_separator=",",
        date_format="%Y年%m月%d日",
        datetime_format="%Y年%m月%d日 %H:%M",
        time_format="%H:%M",
        month_names=["一月", "二月", "三月", "四月", "五月", "六月",
                     "七月", "八月", "九月", "十月", "十一月", "十二月"],
        month_abbrevs=["1月", "2月", "3月", "4月", "5月", "6月",
                       "7月", "8月", "9月", "10月", "11月", "12月"],
        day_names=["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"],
        day_abbrevs=["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
        currency_symbol="¥",
        currency_code="CNY",
        currency_position="before",
    ),
    "ja": LocaleConfig(
        code="ja",
        decimal_separator=".",
        thousands_separator=",",
        date_format="%Y年%m月%d日",
        datetime_format="%Y年%m月%d日 %H時%M分",
        time_format="%H時%M分",
        month_names=["1月", "2月", "3月", "4月", "5月", "6月",
                     "7月", "8月", "9月", "10月", "11月", "12月"],
        month_abbrevs=["1月", "2月", "3月", "4月", "5月", "6月",
                       "7月", "8月", "9月", "10月", "11月", "12月"],
        day_names=["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"],
        day_abbrevs=["月", "火", "水", "木", "金", "土", "日"],
        currency_symbol="¥",
        currency_code="JPY",
        currency_position="before",
    ),
    "ko": LocaleConfig(
        code="ko",
        decimal_separator=".",
        thousands_separator=",",
        date_format="%Y년 %m월 %d일",
        datetime_format="%Y년 %m월 %d일 %H시 %M분",
        time_format="%H시 %M분",
        month_names=["1월", "2월", "3월", "4월", "5월", "6월",
                     "7월", "8월", "9월", "10월", "11월", "12월"],
        month_abbrevs=["1월", "2월", "3월", "4월", "5월", "6월",
                       "7월", "8월", "9월", "10월", "11월", "12월"],
        day_names=["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"],
        day_abbrevs=["월", "화", "수", "목", "금", "토", "일"],
        currency_symbol="₩",
        currency_code="KRW",
        currency_position="before",
    ),
    "ar": LocaleConfig(
        code="ar",
        decimal_separator="٫",
        thousands_separator="٬",
        date_format="%d %B %Y",
        datetime_format="%d %B %Y %H:%M",
        time_format="%H:%M",
        month_names=["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                     "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
        month_abbrevs=["ينا", "فبر", "مار", "أبر", "ماي", "يون",
                       "يول", "أغس", "سبت", "أكت", "نوف", "ديس"],
        day_names=["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"],
        day_abbrevs=["اث", "ثل", "أر", "خم", "جم", "سب", "أح"],
        currency_symbol="ر.س",
        currency_code="SAR",
        currency_position="after",
        rtl=True,
    ),
    "ru": LocaleConfig(
        code="ru",
        decimal_separator=",",
        thousands_separator=" ",
        date_format="%d %B %Y г.",
        datetime_format="%d %B %Y г. %H:%M",
        time_format="%H:%M",
        month_names=["января", "февраля", "марта", "апреля", "мая", "июня",
                     "июля", "августа", "сентября", "октября", "ноября", "декабря"],
        month_abbrevs=["янв", "фев", "мар", "апр", "май", "июн",
                       "июл", "авг", "сен", "окт", "ноя", "дек"],
        day_names=["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"],
        day_abbrevs=["пн", "вт", "ср", "чт", "пт", "сб", "вс"],
        currency_symbol="₽",
        currency_code="RUB",
        currency_position="after",
    ),
}


# ==============================================================================
# Locale Formatter
# ==============================================================================

class LocaleFormatter:
    """Locale-aware formatter for numbers, dates, and currencies.
    
    Usage:
        formatter = LocaleFormatter("es")
        
        # Format number
        formatter.format_number(1234567.89)  # "1.234.567,89"
        
        # Format date
        formatter.format_date(datetime.now())  # "15 de enero de 2025"
        
        # Format currency
        formatter.format_currency(99.99)  # "99,99 €"
    """
    
    def __init__(self, locale_code: str = "en"):
        self.locale_code = locale_code
        self.config = LOCALE_CONFIGS.get(
            locale_code,
            LOCALE_CONFIGS.get("en", LocaleConfig(code="en"))
        )
    
    def format_number(
        self,
        value: Union[int, float, Decimal],
        decimal_places: int = 2,
        use_thousands_separator: bool = True,
    ) -> str:
        """
        Format a number according to locale.
        
        Args:
            value: Number to format
            decimal_places: Number of decimal places
            use_thousands_separator: Whether to use thousands separator
            
        Returns:
            Formatted number string
        """
        # Convert to float
        num = float(value)
        
        # Handle negative
        negative = num < 0
        num = abs(num)
        
        # Split into integer and decimal parts
        if decimal_places > 0:
            format_str = f"{{:.{decimal_places}f}}"
            formatted = format_str.format(num)
            int_part, dec_part = formatted.split(".")
        else:
            int_part = str(int(round(num)))
            dec_part = ""
        
        # Add thousands separator
        if use_thousands_separator and len(int_part) > 3:
            parts = []
            while int_part:
                parts.append(int_part[-3:])
                int_part = int_part[:-3]
            int_part = self.config.thousands_separator.join(reversed(parts))
        
        # Combine
        if dec_part:
            result = f"{int_part}{self.config.decimal_separator}{dec_part}"
        else:
            result = int_part
        
        if negative:
            result = f"-{result}"
        
        return result
    
    def format_integer(self, value: int) -> str:
        """Format an integer with thousands separator."""
        return self.format_number(value, decimal_places=0)
    
    def format_percentage(
        self,
        value: float,
        decimal_places: int = 1,
    ) -> str:
        """Format a percentage."""
        formatted = self.format_number(value * 100, decimal_places)
        return f"{formatted}%"
    
    def format_date(
        self,
        dt: Union[datetime, date],
        format_type: str = "full",
    ) -> str:
        """
        Format a date according to locale.
        
        Args:
            dt: Date or datetime to format
            format_type: "full", "short", "datetime", "time"
            
        Returns:
            Formatted date string
        """
        if format_type == "short":
            format_str = "%d/%m/%Y" if self.locale_code != "en" else "%m/%d/%Y"
        elif format_type == "datetime":
            format_str = self.config.datetime_format
        elif format_type == "time":
            format_str = self.config.time_format
        else:
            format_str = self.config.date_format
        
        # Replace month names
        result = dt.strftime(format_str)
        
        # Replace %B with localized month name
        if "%B" in format_str and self.config.month_names:
            month_idx = dt.month - 1
            result = result.replace(
                dt.strftime("%B"),
                self.config.month_names[month_idx]
            )
        
        # Replace %b with localized abbreviation
        if "%b" in format_str and self.config.month_abbrevs:
            month_idx = dt.month - 1
            result = result.replace(
                dt.strftime("%b"),
                self.config.month_abbrevs[month_idx]
            )
        
        return result
    
    def format_relative_date(self, dt: datetime) -> str:
        """Format a date relative to now (e.g., "2 days ago")."""
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        diff = now - dt
        seconds = diff.total_seconds()
        
        # Relative time strings by locale
        relative_strings = {
            "en": {
                "now": "just now",
                "minute": "{n} minute ago",
                "minutes": "{n} minutes ago",
                "hour": "{n} hour ago",
                "hours": "{n} hours ago",
                "day": "{n} day ago",
                "days": "{n} days ago",
            },
            "es": {
                "now": "ahora mismo",
                "minute": "hace {n} minuto",
                "minutes": "hace {n} minutos",
                "hour": "hace {n} hora",
                "hours": "hace {n} horas",
                "day": "hace {n} día",
                "days": "hace {n} días",
            },
            "fr": {
                "now": "à l'instant",
                "minute": "il y a {n} minute",
                "minutes": "il y a {n} minutes",
                "hour": "il y a {n} heure",
                "hours": "il y a {n} heures",
                "day": "il y a {n} jour",
                "days": "il y a {n} jours",
            },
            "de": {
                "now": "gerade eben",
                "minute": "vor {n} Minute",
                "minutes": "vor {n} Minuten",
                "hour": "vor {n} Stunde",
                "hours": "vor {n} Stunden",
                "day": "vor {n} Tag",
                "days": "vor {n} Tagen",
            },
        }
        
        strings = relative_strings.get(
            self.locale_code,
            relative_strings["en"]
        )
        
        if seconds < 60:
            return strings["now"]
        elif seconds < 3600:
            n = int(seconds / 60)
            key = "minute" if n == 1 else "minutes"
            return strings[key].format(n=n)
        elif seconds < 86400:
            n = int(seconds / 3600)
            key = "hour" if n == 1 else "hours"
            return strings[key].format(n=n)
        else:
            n = int(seconds / 86400)
            key = "day" if n == 1 else "days"
            return strings[key].format(n=n)
    
    def format_currency(
        self,
        value: Union[int, float, Decimal],
        currency_code: Optional[str] = None,
        symbol: Optional[str] = None,
    ) -> str:
        """
        Format a currency value.
        
        Args:
            value: Amount
            currency_code: Override currency code
            symbol: Override currency symbol
            
        Returns:
            Formatted currency string
        """
        symbol = symbol or self.config.currency_symbol
        formatted_number = self.format_number(value, decimal_places=2)
        
        if self.config.currency_position == "before":
            return f"{symbol}{formatted_number}"
        else:
            return f"{formatted_number} {symbol}"
    
    def get_day_name(self, weekday: int, abbreviated: bool = False) -> str:
        """Get localized day name (0=Monday)."""
        if abbreviated and self.config.day_abbrevs:
            return self.config.day_abbrevs[weekday]
        elif self.config.day_names:
            return self.config.day_names[weekday]
        return str(weekday)
    
    def get_month_name(self, month: int, abbreviated: bool = False) -> str:
        """Get localized month name (1=January)."""
        idx = month - 1
        if abbreviated and self.config.month_abbrevs:
            return self.config.month_abbrevs[idx]
        elif self.config.month_names:
            return self.config.month_names[idx]
        return str(month)


# ==============================================================================
# Global Functions
# ==============================================================================

_formatters: Dict[str, LocaleFormatter] = {}


def get_locale_formatter(locale_code: str = "en") -> LocaleFormatter:
    """Get or create a locale formatter."""
    if locale_code not in _formatters:
        _formatters[locale_code] = LocaleFormatter(locale_code)
    return _formatters[locale_code]


def format_number(
    value: Union[int, float, Decimal],
    locale_code: str = "en",
    decimal_places: int = 2,
) -> str:
    """Quick helper to format a number."""
    return get_locale_formatter(locale_code).format_number(value, decimal_places)


def format_date(
    dt: Union[datetime, date],
    locale_code: str = "en",
    format_type: str = "full",
) -> str:
    """Quick helper to format a date."""
    return get_locale_formatter(locale_code).format_date(dt, format_type)


def format_currency(
    value: Union[int, float, Decimal],
    locale_code: str = "en",
) -> str:
    """Quick helper to format currency."""
    return get_locale_formatter(locale_code).format_currency(value)


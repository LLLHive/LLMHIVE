"""
Advanced Scientific Calculator for LLMHive
==========================================

A comprehensive scientific calculator supporting:
- Basic arithmetic
- Trigonometric functions (sin, cos, tan, etc.)
- Logarithmic functions (log, log10, log2, ln)
- Special functions (erf, gamma, factorial, etc.)
- Constants (pi, e, phi, etc.)
- Statistics (mean, std, variance)
- Calculus approximations (numerical integration)
- Financial calculations (compound interest, NPV, IRR)

This calculator is AUTHORITATIVE for mathematical operations.
"""

import math
import logging
from typing import Any, Dict, Optional, Union, List
from decimal import Decimal, ROUND_HALF_UP
import re

logger = logging.getLogger(__name__)


# =============================================================================
# SCIENTIFIC CONSTANTS
# =============================================================================

CONSTANTS = {
    # Mathematical constants
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "phi": (1 + math.sqrt(5)) / 2,  # Golden ratio
    "euler_gamma": 0.5772156649015329,  # Euler-Mascheroni constant
    "sqrt2": math.sqrt(2),
    "sqrt3": math.sqrt(3),
    "ln2": math.log(2),
    "ln10": math.log(10),
    
    # Physical constants (SI units)
    "c": 299792458,  # Speed of light (m/s)
    "g": 9.80665,  # Standard gravity (m/s²)
    "G": 6.67430e-11,  # Gravitational constant
    "h": 6.62607015e-34,  # Planck constant (J·s)
    "hbar": 1.054571817e-34,  # Reduced Planck constant
    "k_B": 1.380649e-23,  # Boltzmann constant (J/K)
    "N_A": 6.02214076e23,  # Avogadro's number
    "R": 8.314462618,  # Gas constant (J/(mol·K))
    "e_charge": 1.602176634e-19,  # Elementary charge (C)
    "m_e": 9.1093837015e-31,  # Electron mass (kg)
    "m_p": 1.67262192369e-27,  # Proton mass (kg)
    "epsilon_0": 8.8541878128e-12,  # Vacuum permittivity
    "mu_0": 1.25663706212e-6,  # Vacuum permeability
}


# =============================================================================
# SPECIAL MATHEMATICAL FUNCTIONS
# =============================================================================

def factorial(n: int) -> int:
    """Calculate factorial of n."""
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n > 170:
        raise ValueError("Factorial overflow for n > 170")
    return math.factorial(int(n))


def double_factorial(n: int) -> int:
    """Calculate double factorial n!! = n * (n-2) * (n-4) * ..."""
    if n < 0:
        raise ValueError("Double factorial not defined for negative numbers")
    result = 1
    while n > 1:
        result *= n
        n -= 2
    return result


def gamma(x: float) -> float:
    """Gamma function Γ(x)."""
    return math.gamma(x)


def lgamma(x: float) -> float:
    """Natural log of gamma function."""
    return math.lgamma(x)


def erf(x: float) -> float:
    """Error function erf(x)."""
    return math.erf(x)


def erfc(x: float) -> float:
    """Complementary error function erfc(x) = 1 - erf(x)."""
    return math.erfc(x)


def beta(a: float, b: float) -> float:
    """Beta function B(a,b) = Γ(a)Γ(b)/Γ(a+b)."""
    return math.gamma(a) * math.gamma(b) / math.gamma(a + b)


def binomial(n: int, k: int) -> int:
    """Binomial coefficient C(n,k) = n! / (k! * (n-k)!)."""
    return math.comb(int(n), int(k))


def permutations(n: int, k: int) -> int:
    """Permutations P(n,k) = n! / (n-k)!."""
    return math.perm(int(n), int(k))


def gcd(a: int, b: int) -> int:
    """Greatest common divisor."""
    return math.gcd(int(a), int(b))


def lcm(a: int, b: int) -> int:
    """Least common multiple."""
    return math.lcm(int(a), int(b))


def is_prime(n: int) -> bool:
    """Check if n is prime."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        if n % i == 0:
            return False
    return True


def prime_factors(n: int) -> List[int]:
    """Return list of prime factors of n."""
    factors = []
    n = int(n)
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors


# =============================================================================
# TRIGONOMETRIC FUNCTIONS (RADIANS AND DEGREES)
# =============================================================================

def sind(x: float) -> float:
    """Sine in degrees."""
    return math.sin(math.radians(x))


def cosd(x: float) -> float:
    """Cosine in degrees."""
    return math.cos(math.radians(x))


def tand(x: float) -> float:
    """Tangent in degrees."""
    return math.tan(math.radians(x))


def asind(x: float) -> float:
    """Arc sine returning degrees."""
    return math.degrees(math.asin(x))


def acosd(x: float) -> float:
    """Arc cosine returning degrees."""
    return math.degrees(math.acos(x))


def atand(x: float) -> float:
    """Arc tangent returning degrees."""
    return math.degrees(math.atan(x))


def atan2d(y: float, x: float) -> float:
    """Two-argument arc tangent returning degrees."""
    return math.degrees(math.atan2(y, x))


# Hyperbolic functions are already in math module
sinh = math.sinh
cosh = math.cosh
tanh = math.tanh
asinh = math.asinh
acosh = math.acosh
atanh = math.atanh


# =============================================================================
# NUMERICAL INTEGRATION (for integrals like ∫e^(x²))
# =============================================================================

def integrate(f, a: float, b: float, n: int = 1000) -> float:
    """
    Numerical integration using Simpson's rule.
    
    Args:
        f: Function to integrate (callable)
        a: Lower bound
        b: Upper bound
        n: Number of intervals (must be even)
    
    Returns:
        Approximate integral value
    """
    if n % 2 == 1:
        n += 1
    
    h = (b - a) / n
    result = f(a) + f(b)
    
    for i in range(1, n):
        x = a + i * h
        if i % 2 == 0:
            result += 2 * f(x)
        else:
            result += 4 * f(x)
    
    return result * h / 3


def integrate_exp_x_squared(a: float = 0, b: float = 1) -> float:
    """
    Specifically compute ∫e^(x²)dx from a to b.
    
    This is a non-elementary integral related to the error function.
    For ∫e^(x²)dx from 0 to 1, the result is approximately 1.4627...
    
    This can also be expressed as: (√π/2) * erfi(x)
    where erfi(x) is the imaginary error function.
    """
    def f(x):
        return math.exp(x * x)
    
    return integrate(f, a, b, n=10000)


def dawson_integral(x: float) -> float:
    """
    Dawson's integral D(x) = e^(-x²) * ∫e^(t²)dt from 0 to x.
    
    This is related to the error function.
    """
    def f(t):
        return math.exp(t * t)
    
    if abs(x) < 1e-10:
        return 0.0
    
    integral = integrate(f, 0, x, n=1000)
    return math.exp(-x * x) * integral


# =============================================================================
# FINANCIAL CALCULATIONS
# =============================================================================

def compound_interest(
    principal: float,
    rate: float,
    periods: int,
    compounds_per_period: int = 1
) -> float:
    """
    Calculate compound interest.
    
    A = P(1 + r/n)^(nt)
    
    Args:
        principal: Initial amount
        rate: Interest rate per period (as decimal, e.g., 0.05 for 5%)
        periods: Number of time periods
        compounds_per_period: Times interest compounds per period
    
    Returns:
        Final amount after compound interest
    """
    n = compounds_per_period
    t = periods
    r = rate
    return principal * (1 + r/n) ** (n * t)


def present_value(
    future_value: float,
    rate: float,
    periods: int
) -> float:
    """Calculate present value of future money."""
    return future_value / ((1 + rate) ** periods)


def future_value(
    present_value_amount: float,
    rate: float,
    periods: int
) -> float:
    """Calculate future value of present money."""
    return present_value_amount * ((1 + rate) ** periods)


def npv(rate: float, cash_flows: List[float]) -> float:
    """
    Net Present Value of a series of cash flows.
    
    Args:
        rate: Discount rate (as decimal)
        cash_flows: List of cash flows (first is typically initial investment, negative)
    """
    return sum(cf / ((1 + rate) ** i) for i, cf in enumerate(cash_flows))


def annuity_pv(payment: float, rate: float, periods: int) -> float:
    """Present value of an ordinary annuity."""
    if rate == 0:
        return payment * periods
    return payment * (1 - (1 + rate) ** (-periods)) / rate


def annuity_fv(payment: float, rate: float, periods: int) -> float:
    """Future value of an ordinary annuity."""
    if rate == 0:
        return payment * periods
    return payment * ((1 + rate) ** periods - 1) / rate


def mortgage_payment(principal: float, annual_rate: float, years: int) -> float:
    """Calculate monthly mortgage payment."""
    r = annual_rate / 12  # Monthly rate
    n = years * 12  # Total payments
    if r == 0:
        return principal / n
    return principal * (r * (1 + r) ** n) / ((1 + r) ** n - 1)


# =============================================================================
# STATISTICS
# =============================================================================

def mean(values: List[float]) -> float:
    """Calculate arithmetic mean."""
    return sum(values) / len(values)


def geometric_mean(values: List[float]) -> float:
    """Calculate geometric mean."""
    product = 1
    for v in values:
        product *= v
    return product ** (1 / len(values))


def harmonic_mean(values: List[float]) -> float:
    """Calculate harmonic mean."""
    return len(values) / sum(1/v for v in values)


def median(values: List[float]) -> float:
    """Calculate median."""
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n % 2 == 1:
        return sorted_vals[n // 2]
    return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2


def mode(values: List[float]) -> float:
    """Calculate mode (most frequent value)."""
    from collections import Counter
    counts = Counter(values)
    return max(counts.items(), key=lambda x: x[1])[0]


def variance(values: List[float], sample: bool = True) -> float:
    """Calculate variance."""
    m = mean(values)
    n = len(values)
    divisor = n - 1 if sample else n
    return sum((x - m) ** 2 for x in values) / divisor


def std_dev(values: List[float], sample: bool = True) -> float:
    """Calculate standard deviation."""
    return math.sqrt(variance(values, sample))


def correlation(x: List[float], y: List[float]) -> float:
    """Calculate Pearson correlation coefficient."""
    n = len(x)
    mean_x = mean(x)
    mean_y = mean(y)
    
    numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    denom_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
    denom_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))
    
    return numerator / (denom_x * denom_y)


# =============================================================================
# UNIT CONVERSIONS
# =============================================================================

CONVERSIONS = {
    # Length
    ("km", "miles"): 0.621371,
    ("miles", "km"): 1.60934,
    ("m", "ft"): 3.28084,
    ("ft", "m"): 0.3048,
    ("cm", "in"): 0.393701,
    ("in", "cm"): 2.54,
    
    # Weight
    ("kg", "lb"): 2.20462,
    ("lb", "kg"): 0.453592,
    ("g", "oz"): 0.035274,
    ("oz", "g"): 28.3495,
    
    # Temperature (handled separately)
    
    # Volume
    ("L", "gal"): 0.264172,
    ("gal", "L"): 3.78541,
    
    # Area
    ("m2", "ft2"): 10.7639,
    ("ft2", "m2"): 0.092903,
    ("km2", "mi2"): 0.386102,
    ("mi2", "km2"): 2.58999,
    ("ha", "acre"): 2.47105,
    ("acre", "ha"): 0.404686,
}


def convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    """Convert temperature between Celsius, Fahrenheit, and Kelvin."""
    from_unit = from_unit.upper()
    to_unit = to_unit.upper()
    
    # Convert to Celsius first
    if from_unit == "F":
        celsius = (value - 32) * 5/9
    elif from_unit == "K":
        celsius = value - 273.15
    else:
        celsius = value
    
    # Convert from Celsius to target
    if to_unit == "F":
        return celsius * 9/5 + 32
    elif to_unit == "K":
        return celsius + 273.15
    else:
        return celsius


def convert_unit(value: float, from_unit: str, to_unit: str) -> float:
    """General unit conversion."""
    key = (from_unit.lower(), to_unit.lower())
    if key in CONVERSIONS:
        return value * CONVERSIONS[key]
    
    # Check for temperature
    if from_unit.upper() in ("C", "F", "K") and to_unit.upper() in ("C", "F", "K"):
        return convert_temperature(value, from_unit, to_unit)
    
    raise ValueError(f"Unknown conversion: {from_unit} to {to_unit}")


# =============================================================================
# MAIN CALCULATOR CLASS
# =============================================================================

class ScientificCalculator:
    """
    Advanced scientific calculator with comprehensive function support.
    
    This calculator is AUTHORITATIVE for all mathematical operations.
    """
    
    def __init__(self):
        """Initialize the calculator with all functions and constants."""
        # Build the safe evaluation namespace
        self.safe_namespace = {
            # Disable builtins for security
            "__builtins__": {},
            
            # Basic functions
            "abs": abs,
            "round": round,
            "int": int,
            "float": float,
            "min": min,
            "max": max,
            "sum": sum,
            "len": len,
            "pow": pow,
            
            # Math module basics
            "sqrt": math.sqrt,
            "cbrt": lambda x: x ** (1/3),
            "exp": math.exp,
            "log": math.log,
            "log10": math.log10,
            "log2": math.log2,
            "ln": math.log,
            
            # Trigonometric (radians)
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "asin": math.asin,
            "acos": math.acos,
            "atan": math.atan,
            "atan2": math.atan2,
            
            # Trigonometric (degrees)
            "sind": sind,
            "cosd": cosd,
            "tand": tand,
            "asind": asind,
            "acosd": acosd,
            "atand": atand,
            "atan2d": atan2d,
            
            # Hyperbolic
            "sinh": math.sinh,
            "cosh": math.cosh,
            "tanh": math.tanh,
            "asinh": math.asinh,
            "acosh": math.acosh,
            "atanh": math.atanh,
            
            # Special functions
            "factorial": factorial,
            "double_factorial": double_factorial,
            "gamma": gamma,
            "lgamma": lgamma,
            "erf": erf,
            "erfc": erfc,
            "beta": beta,
            "binomial": binomial,
            "comb": binomial,
            "perm": permutations,
            "gcd": gcd,
            "lcm": lcm,
            "is_prime": is_prime,
            "prime_factors": prime_factors,
            
            # Integration
            "integrate": integrate,
            "integrate_exp_x2": integrate_exp_x_squared,
            "dawson": dawson_integral,
            
            # Financial
            "compound_interest": compound_interest,
            "present_value": present_value,
            "future_value": future_value,
            "npv": npv,
            "annuity_pv": annuity_pv,
            "annuity_fv": annuity_fv,
            "mortgage_payment": mortgage_payment,
            
            # Statistics
            "mean": mean,
            "geometric_mean": geometric_mean,
            "harmonic_mean": harmonic_mean,
            "median": median,
            "mode": mode,
            "variance": variance,
            "std_dev": std_dev,
            "correlation": correlation,
            
            # Unit conversion
            "convert_unit": convert_unit,
            "convert_temp": convert_temperature,
            
            # Floor/ceiling
            "floor": math.floor,
            "ceil": math.ceil,
            "trunc": math.trunc,
            
            # Rounding
            "degrees": math.degrees,
            "radians": math.radians,
            
            # Misc
            "copysign": math.copysign,
            "fabs": math.fabs,
            "fmod": math.fmod,
            "modf": math.modf,
            "isnan": math.isnan,
            "isinf": math.isinf,
            "isfinite": math.isfinite,
        }
        
        # Add all constants
        self.safe_namespace.update(CONSTANTS)
    
    def sanitize_expression(self, expr: str) -> str:
        """
        Sanitize and normalize a mathematical expression.
        
        Args:
            expr: Raw expression string
            
        Returns:
            Cleaned expression safe for evaluation
        """
        # Remove dangerous patterns
        dangerous = ["import", "exec", "eval", "open", "file", "__", "os.", "sys."]
        expr_lower = expr.lower()
        for pattern in dangerous:
            if pattern in expr_lower:
                raise ValueError(f"Expression contains forbidden pattern: {pattern}")
        
        # Normalize operators
        expr = expr.replace("×", "*")
        expr = expr.replace("÷", "/")
        expr = expr.replace("^", "**")
        expr = expr.replace("²", "**2")
        expr = expr.replace("³", "**3")
        
        # Handle implicit multiplication: 2x -> 2*x, 3pi -> 3*pi
        expr = re.sub(r'(\d)([a-zA-Z_])', r'\1*\2', expr)
        expr = re.sub(r'(\))(\d)', r'\1*\2', expr)
        expr = re.sub(r'(\d)(\()', r'\1*\2', expr)
        
        return expr.strip()
    
    def evaluate(self, expression: str) -> Dict[str, Any]:
        """
        Evaluate a mathematical expression.
        
        Args:
            expression: Mathematical expression to evaluate
            
        Returns:
            Dictionary with result, success, and metadata
        """
        try:
            # Sanitize the expression
            clean_expr = self.sanitize_expression(expression)
            
            if not clean_expr:
                return {
                    "success": False,
                    "error": "Empty expression",
                    "expression": expression,
                }
            
            # Handle special integral cases
            if "integral" in expression.lower() or "∫" in expression:
                if "e^(x²)" in expression or "e^x^2" in expression.lower():
                    result = integrate_exp_x_squared()
                    return {
                        "success": True,
                        "result": result,
                        "formatted": f"{result:.6f}",
                        "expression": expression,
                        "note": "∫e^(x²)dx from 0 to 1 ≈ 1.4627 (related to erf)"
                    }
            
            # Evaluate the expression
            result = eval(clean_expr, self.safe_namespace)
            
            # Format the result
            if isinstance(result, float):
                # Round to avoid floating point artifacts
                if abs(result) < 1e10 and abs(result) > 1e-10:
                    formatted = f"{result:.6g}"
                else:
                    formatted = f"{result:.6e}"
            elif isinstance(result, bool):
                formatted = str(result)
            elif isinstance(result, (list, tuple)):
                formatted = str(result)
            else:
                formatted = str(result)
            
            return {
                "success": True,
                "result": result,
                "formatted": formatted,
                "expression": clean_expr,
            }
            
        except ZeroDivisionError:
            return {
                "success": False,
                "error": "Division by zero",
                "expression": expression,
            }
        except OverflowError:
            return {
                "success": False,
                "error": "Numerical overflow",
                "expression": expression,
            }
        except ValueError as e:
            return {
                "success": False,
                "error": f"Math domain error: {str(e)}",
                "expression": expression,
            }
        except Exception as e:
            logger.warning("Calculator evaluation failed: %s", e)
            return {
                "success": False,
                "error": str(e),
                "expression": expression,
            }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_calculator: Optional[ScientificCalculator] = None


def get_calculator() -> ScientificCalculator:
    """Get or create the global calculator instance."""
    global _calculator
    if _calculator is None:
        _calculator = ScientificCalculator()
    return _calculator


def calculate(expression: str) -> Dict[str, Any]:
    """
    Convenience function to evaluate an expression.
    
    Args:
        expression: Mathematical expression
        
    Returns:
        Result dictionary
    """
    return get_calculator().evaluate(expression)


def execute_calculation(expression: str) -> Optional[float]:
    """
    Execute a calculation and return just the numeric result.
    
    This is the AUTHORITATIVE function for mathematical operations.
    The calculator result should ALWAYS be trusted over LLM inference.
    
    Args:
        expression: Mathematical expression
        
    Returns:
        Numeric result or None if calculation failed
    """
    result = calculate(expression)
    if result.get("success"):
        val = result.get("result")
        if isinstance(val, (int, float)):
            return float(val)
        return val
    return None


# =============================================================================
# MATH CHEAT SHEET DATA
# =============================================================================

MATH_CHEAT_SHEET = """
# LLMHive Mathematical Reference Cheat Sheet

## Basic Operations
- Addition: a + b
- Subtraction: a - b
- Multiplication: a * b or a × b
- Division: a / b or a ÷ b
- Power: a ** b or a ^ b
- Square root: sqrt(x)
- Cube root: cbrt(x) or x ** (1/3)

## Constants
- π (pi) = 3.14159265358979...
- e (Euler's number) = 2.71828182845904...
- τ (tau) = 2π = 6.28318...
- φ (golden ratio) = 1.61803398875...
- √2 = 1.41421356...
- √3 = 1.73205080...

## Trigonometry (radians)
- sin(x), cos(x), tan(x)
- asin(x), acos(x), atan(x), atan2(y, x)
- sinh(x), cosh(x), tanh(x) - hyperbolic

## Trigonometry (degrees)
- sind(x), cosd(x), tand(x)
- asind(x), acosd(x), atand(x)

## Logarithms
- ln(x) or log(x) - natural log (base e)
- log10(x) - base 10 logarithm
- log2(x) - base 2 logarithm
- log(x, base) - logarithm with custom base

## Special Functions
- erf(x) - Error function
- erfc(x) - Complementary error function (1 - erf(x))
- gamma(x) - Gamma function Γ(x)
- factorial(n) or n! - Factorial
- binomial(n, k) - Binomial coefficient C(n,k)

## Number Theory
- gcd(a, b) - Greatest common divisor
- lcm(a, b) - Least common multiple
- is_prime(n) - Check if prime
- prime_factors(n) - List of prime factors

## Statistics
- mean([values]) - Arithmetic mean
- median([values]) - Median value
- std_dev([values]) - Standard deviation
- variance([values]) - Variance
- correlation(x, y) - Pearson correlation

## Financial
- compound_interest(P, r, t, n) - A = P(1 + r/n)^(nt)
  * P = principal
  * r = annual rate (decimal, e.g., 0.05 for 5%)
  * t = time in years
  * n = compounds per year (12 for monthly)

## Numerical Integration
- integrate(f, a, b) - ∫f(x)dx from a to b
- integrate_exp_x2() - ∫e^(x²)dx from 0 to 1 ≈ 1.4627

## Key Formulas
- Circle area: A = π * r²
- Circle circumference: C = 2 * π * r
- Sphere volume: V = (4/3) * π * r³
- Triangle area: A = 0.5 * base * height
- Quadratic: x = (-b ± sqrt(b² - 4ac)) / (2a)
- Distance: d = sqrt((x₂-x₁)² + (y₂-y₁)²)

## Integral of e^(x²)
The integral ∫e^(x²)dx is non-elementary (cannot be expressed with basic functions).
For the definite integral from 0 to 1:
∫₀¹ e^(x²) dx ≈ 1.4627 (to 4 decimal places)

This is related to the imaginary error function erfi(x).
"""


if __name__ == "__main__":
    # Test the calculator
    calc = ScientificCalculator()
    
    tests = [
        "2 + 2",
        "sqrt(16)",
        "pi * 4",
        "erf(1)",
        "factorial(5)",
        "compound_interest(10000, 0.05, 10, 12)",
        "integrate_exp_x2()",
        "binomial(8, 3)",
        "sind(30)",  # sin(30°) = 0.5
    ]
    
    for expr in tests:
        result = calc.evaluate(expr)
        print(f"{expr} = {result.get('formatted', result.get('error'))}")

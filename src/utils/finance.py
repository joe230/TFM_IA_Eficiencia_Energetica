def convert_energy_to_cost(energy_kwh: float, price_kwh: float = 0.15) -> float:
    """
    Calculate the cost in euros from energy in Kilowatt-hours (kWh) applying a regulated or fixed tariff.
    """
    return float(energy_kwh * price_kwh)
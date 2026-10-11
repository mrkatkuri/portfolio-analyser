def observations(holdings, threshold):
    messages = []
    for row in holdings[holdings.weight_pct > threshold].itertuples():
        messages.append(f'{row.symbol} accounts for {row.weight_pct:.1f}% of current value, above your {threshold}% limit.')
    for sector, weight in holdings.groupby('sector').weight_pct.sum().items():
        if weight > 40:
            messages.append(f'{sector} represents {weight:.1f}% of current value.')
    for row in holdings[holdings.total_gain < 0].itertuples():
        messages.append(f'{row.symbol} has a loss of {abs(row.total_gain):,.2f} in the base currency, including realised gains/losses.')
    return messages or ['No holdings breach the selected concentration limit and no stocks have a net loss.']

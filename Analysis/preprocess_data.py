import json
import math
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Zip code -> HRR
zip2HRR = {}
zip_hrr_df = pd.read_excel('../Data/ziphsahrr00.xls')
for index, row in zip_hrr_df.iterrows():
    padded_zip = str(row['zipcode00']).zfill(5) # The leading zeroes may have been wiped out in the crosswalk file. Add them back if necessary
    zip2HRR[padded_zip] = row['hrrnum']

# Zip code -> Fips -> market (from the detection algorithm)
with open('../Data/zip2fips.json', 'r') as file:
    jsonString = file.read().rstrip()
    zip2fips = json.loads(jsonString)
fips2mkt = {}
with open('../Data/hospital_markets.txt', 'r') as file:
    leading_line = True # The first line is column names. Ignore them
    for line in file:
        if leading_line:
            leading_line = False
            continue
        line = line.replace(" ", "")
        segs = line.split('"')
        fips2mkt[segs[1]] = segs[2]
zip2mkt = {}
for zip, fips in zip2fips.items():
    if fips in fips2mkt: # Some fips don't have an associated market, for some reason I don't know
        zip2mkt[zip] = fips2mkt[fips]

# Read data
df = pd.read_csv('../Data/HCRIS_Data.txt', delimiter = "\t")
#df = df[['provider_number', 'tot_discharges', 'zip', 'year', 'tot_charges', 'beds', 'cost_to_charge']]

# Look at only years 2000-2017
df = df[df['year'].apply(lambda x: (x <= 2017) & (x >= 2000))]

# Drop obs with missing values for discharges. This drops from 124, 443 -> 122, 504
print(f'Num of obs: {len(df.index)}')
df = df[df['tot_discharges'].apply(lambda x: math.isnan(x) == False)]
print(f'Num of obs: {len(df.index)}')

# Clean zip codes
# Some zip codes are ill-formated like "36301-" or "363010000". Keep only the first 5 digits
# This drops 8,720 obs. Not ideal, but I doubt it matters
df['zip'] = df['zip'].apply(lambda x: str(x)[:5]) 
def known_zip(zip): # We don't have crosswalks for certain zip codes, so drop them.
    return zip in zip2HRR and zip in zip2mkt
df = df[df['zip'].apply(known_zip)]
df['hrr'] = df['zip'].apply(lambda x: zip2HRR[x])
df['mkt'] = df['zip'].apply(lambda x: zip2mkt[x])
print(f'Num of obs: {len(df.index)}')

# Calculate HHI
def calculate_hhi(market_def):
    markets_years_df = pd.DataFrame(columns =  [market_def, "year", f'{market_def}_hhi', f'{market_def}_tot_discharges'])
    for year in range(2000, 2018): # 2000-2017
        year_df = df[df['year'] == year]
        uniq_markets = set(df[market_def])
        for market in uniq_markets:
            market_df = year_df[year_df[market_def] == market]
            market_total_discharges = market_df['tot_discharges'].sum()
            market_hhi = sum([(discharge*100 / market_total_discharges)**2 for discharge in market_df['tot_discharges'].tolist()])
            market_hhi= round(market_hhi, 2)
            markets_years_df = markets_years_df._append({market_def: market, 'year': year, f'{market_def}_hhi': market_hhi, f'{market_def}_tot_discharges': market_total_discharges}, ignore_index=True)
    return markets_years_df

# For each market definiation, calculate market share + HHI
zip_hhi_by_year = calculate_hhi('zip') # This has about 97478 obs
hrr_hhi_by_year = calculate_hhi('hrr')
mkt_hhi_by_year = calculate_hhi('mkt')

# Now, merge HHI with original dataframe
df = pd.merge(df, zip_hhi_by_year,  how='left', on=['zip','year'])
df = pd.merge(df, hrr_hhi_by_year,  how='left', on=['hrr','year'])
df = pd.merge(df, mkt_hhi_by_year,  how='left', on=['mkt','year'])

# Now calculate each hospital's market share by year
df['zip_share'] = 0
df['hrr_share'] = 0
df['mkt_share'] = 0
for index, row in df.iterrows():
    df.at[index, 'zip_share'] = round(row['tot_discharges'] / row['zip_tot_discharges'] * 100, 2)
    df.at[index, 'hrr_share'] = round(row['tot_discharges'] / row['hrr_tot_discharges'] * 100, 2)
    df.at[index, 'mkt_share'] = round(row['tot_discharges'] / row['mkt_tot_discharges'] * 100, 2)

# Draw a violin plot of hospital shares over time
sns.violinplot(data=df, x="year", y="zip_share")
plt.show()
sns.violinplot(data=df, x="year", y="hrr_share")
plt.show()
sns.violinplot(data=df, x="year", y="mkt_share")
plt.show()

# Now, save the data for analysis in stata
df['year'] = df['year'].apply(lambda x: str(x))
df.to_stata('0416.dta', version=117)

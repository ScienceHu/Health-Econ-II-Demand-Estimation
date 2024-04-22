cd "C:\Users\zyan385\OneDrive - Emory University\Desktop\Health Econ 2\Demand Estimation\MyOwn"
use 0416.dta

/*Calculate price*/
gen discount_factor = 1 - tot_discounts/tot_charges
gen price_num = (ip_charges + icu_charges + ancillary_charges)*discount_factor - tot_mcare_payment
gen price_denom = tot_discharges_x - mcare_discharges
gen price = price_num / price_denom
drop if missing(price) /*This drops about 53,268 obs*/
drop if missing(beds)

/*Turn year into numeric. Without this, you can't regress on them as an indicator variable*/
destring year, replace ignore(" ")

/*Regress price on HHI with hospital and time fixed effects. I didn't bother 
including other control variables, because this identification strategy (ie. regressing on HHI) 
is bogus any way and controlling for additional variables won't help*/
xtset provider_number
xtreg price zip_hhi i.year beds, fe
xtreg price hrr_hhi i.year beds, fe
xtreg price mkt_hhi i.year beds, fe

/*Esimate a discrete choice model (Berry 1994)*/
gen ln_price = log(price)
gen ln_zip_shares = log(zip_share)
gen ln_hrr_shares = log(hrr_share)
gen ln_mkt_shares = log(mkt_share)
eststo: xtreg ln_zip_shares ln_price i.year beds, fe
eststo: xtreg ln_hrr_shares ln_price i.year beds, fe
eststo: xtreg ln_mkt_shares ln_price i.year beds, fe
esttab, title(Demand estimation (price elasticity of demand). zip code vs. hrr vs. mkt) 
eststo clear
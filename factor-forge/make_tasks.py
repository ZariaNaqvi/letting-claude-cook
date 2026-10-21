import json, sys, os, pandas as pd
B = sys.argv[1]
res = pd.read_csv(os.path.join(B, "data/ground_truth_results.csv")).set_index("task")
VW = "Block 0 of each portfolio file: 'Average Value Weighted Returns -- Monthly' (the FIRST table; monthly rows dated YYYYMM). Do NOT use the equal-weighted, annual, number-of-firms, market-cap/firm-size, or characteristic blocks."
OUT = "Write output.csv with columns date (int YYYYMM) and value (monthly return in percent, same units as the input files), one row per month for every month available in the input."
def t(id_, name, off_file, off_col, inputs, recipe, block_note=VW):
    r = res.loc[id_]
    return dict(id=id_, factor_name=name, official_file=off_file, official_column=off_col,
                official_block="block 0 (untitled monthly table, first table in file)",
                input_files=inputs, block_to_use=block_note, recipe_text=recipe + " " + OUT,
                name_only_text=f"Construct the Fama-French {name} factor exactly as Ken French does, monthly, from the raw files provided ({', '.join(inputs)}). " + OUT,
                truth_csv=f"data/truth/{id_}.csv", reference_csv=f"data/reference/{id_}.csv",
                months=int(r.months), first=int(r["first"]), last=int(r["last"]),
                reference_rmse_bp=round(float(r.rmse_bp),4), reference_max_abs_bp=round(float(r.max_abs_bp),4))
tasks = [
 t("HML","HML (high minus low, value) from the 3-factor model","F-F_Research_Data_Factors.csv","HML",["6_Portfolios_2x3.csv"],
   "HML = 1/2 (Small Value + Big Value) - 1/2 (Small Growth + Big Growth), i.e. 0.5*(SMALL HiBM + BIG HiBM) - 0.5*(SMALL LoBM + BIG LoBM), using the value-weighted monthly returns table (first table) of 6_Portfolios_2x3.csv."),
 t("SMB_3F","SMB (small minus big) from the 3-factor model","F-F_Research_Data_Factors.csv","SMB",["6_Portfolios_2x3.csv"],
   "SMB = 1/3 (Small Value + Small Neutral + Small Growth) - 1/3 (Big Value + Big Neutral + Big Growth), i.e. mean(SMALL LoBM, ME1 BM2, SMALL HiBM) - mean(BIG LoBM, ME2 BM2, BIG HiBM), using the value-weighted monthly returns table (first table) of 6_Portfolios_2x3.csv."),
 t("SMB_5F","SMB (small minus big) from the 5-factor (2x3) model","F-F_Research_Data_5_Factors_2x3.csv","SMB",["6_Portfolios_2x3.csv","6_Portfolios_ME_OP_2x3.csv","6_Portfolios_ME_INV_2x3.csv"],
   "SMB = 1/3 (SMB_B/M + SMB_OP + SMB_INV), where in each of the three 2x3 files SMB_x = mean of the 3 small portfolios - mean of the 3 big portfolios (small = SMALL Lo*, ME1 *2, SMALL Hi*; big = BIG Lo*, ME2 *2, BIG Hi*). Use the value-weighted monthly returns table (first table) of each file, and only months present in all three files (196307 onward)."),
 t("RMW","RMW (robust minus weak profitability)","F-F_Research_Data_5_Factors_2x3.csv","RMW",["6_Portfolios_ME_OP_2x3.csv"],
   "RMW = 1/2 (Small Robust + Big Robust) - 1/2 (Small Weak + Big Weak), i.e. 0.5*(SMALL HiOP + BIG HiOP) - 0.5*(SMALL LoOP + BIG LoOP), using the value-weighted monthly returns table (first table) of 6_Portfolios_ME_OP_2x3.csv."),
 t("CMA","CMA (conservative minus aggressive investment)","F-F_Research_Data_5_Factors_2x3.csv","CMA",["6_Portfolios_ME_INV_2x3.csv"],
   "CMA = 1/2 (Small Conservative + Big Conservative) - 1/2 (Small Aggressive + Big Aggressive), i.e. 0.5*(SMALL LoINV + BIG LoINV) - 0.5*(SMALL HiINV + BIG HiINV), using the value-weighted monthly returns table (first table) of 6_Portfolios_ME_INV_2x3.csv."),
 t("MOM","Momentum (Mom / UMD)","F-F_Momentum_Factor.csv","Mom",["6_Portfolios_ME_Prior_12_2.csv"],
   "Mom = 1/2 (Small High + Big High) - 1/2 (Small Low + Big Low) prior (t-12 to t-2) return, i.e. 0.5*(SMALL HiPRIOR + BIG HiPRIOR) - 0.5*(SMALL LoPRIOR + BIG LoPRIOR), using the value-weighted monthly returns table (first table) of 6_Portfolios_ME_Prior_12_2.csv."),
 t("ST_REV","Short-Term Reversal (ST_Rev)","F-F_ST_Reversal_Factor.csv","ST_Rev",["6_Portfolios_ME_Prior_1_0.csv"],
   "ST_Rev = 1/2 (Small Low + Big Low) - 1/2 (Small High + Big High) prior (t-1) return, i.e. 0.5*(SMALL LoPRIOR + BIG LoPRIOR) - 0.5*(SMALL HiPRIOR + BIG HiPRIOR), using the value-weighted monthly returns table (first table) of 6_Portfolios_ME_Prior_1_0.csv. Note the sign: LOW minus HIGH."),
 t("LT_REV","Long-Term Reversal (LT_Rev)","F-F_LT_Reversal_Factor.csv","LT_Rev",["6_Portfolios_ME_Prior_60_13.csv"],
   "LT_Rev = 1/2 (Small Low + Big Low) - 1/2 (Small High + Big High) prior (t-60 to t-13) return, i.e. 0.5*(SMALL LoPRIOR + BIG LoPRIOR) - 0.5*(SMALL HiPRIOR + BIG HiPRIOR), using the value-weighted monthly returns table (first table) of 6_Portfolios_ME_Prior_60_13.csv. Note the sign: LOW minus HIGH."),
]
worst = max(x["reference_rmse_bp"] for x in tasks)
doc = dict(
  source="Ken French Data Library, files built from the 202608 CRSP database, downloaded 2026-10-21",
  url_pattern="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/<NAME>_CSV.zip",
  pass_rule=dict(script_ran=True, min_coverage=0.95, rmse_bp_max=max(1.0, round(2*worst, 2)),
     note=f"worst human-reference RMSE = {worst} bp (inputs rounded to 2 dp for Prior files, 4 dp for 2x3 files; official factors rounded to 2 dp). Threshold = max(1 bp, 2 x worst reference RMSE)."),
  never_give_model=["F-F_Research_Data_Factors.csv","F-F_Research_Data_5_Factors_2x3.csv","F-F_Momentum_Factor.csv","F-F_ST_Reversal_Factor.csv","F-F_LT_Reversal_Factor.csv"],
  dropped=[dict(id="HML_5F", reason="Official HML in the 5-factor file is byte-identical to the 3-factor HML over 196307-202608 (max diff 0.00); redundant with HML.")],
  tasks=tasks)
json.dump(doc, open(os.path.join(B, "tasks.json"), "w"), indent=2)
print("tasks", [x["id"] for x in tasks], "threshold", doc["pass_rule"]["rmse_bp_max"])

import fs from "node:fs/promises";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const out = new URL("../excel/energy_ledger_management_pack.xlsx", import.meta.url).pathname;
const wb = Workbook.create();
const overview = wb.worksheets.add("Executive Summary");
const scenario = wb.worksheets.add("Scenario");
const exceptions = wb.worksheets.add("Exceptions");
const monthly = wb.worksheets.add("Monthly KPI");
const quality = wb.worksheets.add("Data Quality");
const detail = wb.worksheets.add("Invoice Detail");
const definitions = wb.worksheets.add("Definitions");
const dark = "#17365D", blue = "#1F4E78", light = "#D9EAF7", amber = "#FFF2CC", red = "#FCE4D6", green = "#E2F0D9";
const sheets = [overview,scenario,exceptions,monthly,quality,detail,definitions];
for (const s of sheets) { s.showGridLines = false; s.getRange("A1:Z80").format.font = { name: "Arial", size: 10, color: "#1F1F1F" }; }
function title(s, text, subtitle) { s.getRange("A2").values=[[text]]; s.getRange("A2").format.font={name:"Arial",size:16,bold:true,color:dark}; s.getRange("A3").values=[[subtitle]]; s.getRange("A3").format.font={name:"Arial",size:10,italic:true,color:"#666666"}; s.getRange("A4:H4").format.borders={bottom:{style:"medium",color:blue}}; }
function header(s, range) { const r=s.getRange(range); r.format.fill=blue; r.format.font={name:"Arial",size:10,bold:true,color:"#FFFFFF"}; r.format.horizontalAlignment="center"; r.format.verticalAlignment="center"; }
function widths(s, spec) { for (const [col,w] of Object.entries(spec)) s.getRange(`${col}:${col}`).format.columnWidth=w; }

title(detail,"Invoice detail","Curated invoice lines from the Energy Ledger SQLite model. Refresh source queries before management use.");
const invHeaders=["Invoice line","Site","Account","Billing start","Billing end","Invoice date","Native quantity","Unit","Energy type","kWh equivalent","Invoice amount (INR)","Emissions kgCO2e","Factor ID"];
const invRows=[
["INV-1001-01","Bengaluru HQ","ELEC-7781",new Date("2026-08-01"),new Date("2026-08-31"),new Date("2026-09-03"),12500,"KWH","electricity",12500,156250,8850,"IN-GRID-2026-v1"],
["INV-1002-01","Bengaluru Distribution Centre","ELEC-7782",new Date("2026-08-01"),new Date("2026-08-31"),new Date("2026-09-03"),18600,"KWH","electricity",18600,232500,13168.8,"IN-GRID-2026-v1"],
["INV-1003-01","Delhi Sales Office","ELEC-7783",new Date("2026-08-01"),new Date("2026-08-31"),new Date("2026-09-04"),5400,"KWH","electricity",5400,67500,3823.2,"IN-GRID-2026-v1"],
["INV-1004-01","Bengaluru HQ","GAS-4811",new Date("2026-08-01"),new Date("2026-08-31"),new Date("2026-09-04"),430,"GJ","natural_gas",119444.44454,43000,24127.777797,"IN-GAS-2026-v1"],
["INV-1005-01","Bengaluru Distribution Centre","GAS-4812",new Date("2026-08-01"),new Date("2026-08-31"),new Date("2026-09-04"),250,"GJ","natural_gas",69444.4445,25500,14027.777789,"IN-GAS-2026-v1"],
["INV-1006-01","Delhi Sales Office","ELEC-7783",new Date("2026-08-01"),new Date("2026-08-31"),new Date("2026-09-05"),5600,"KWH","electricity",5600,70000,3964.8,"IN-GRID-2026-v1"]];
detail.getRange("A6:M6").values=[invHeaders]; header(detail,"A6:M6"); detail.getRange("A7:M12").values=invRows; detail.getRange("D7:F12").format.numberFormat="yyyy-mm-dd"; detail.getRange("G7:G12").format.numberFormat="#,#0.0"; detail.getRange("J7:J12").format.numberFormat="#,#0.0"; detail.getRange("K7:K12").format.numberFormat="₹#,##0"; detail.getRange("L7:L12").format.numberFormat="#,#0.0"; detail.freezePanes.freezeRows(6); widths(detail,{A:16,B:28,C:15,D:13,E:13,F:13,G:14,H:10,I:16,J:15,K:18,L:18,M:20});

title(scenario,"Scenario controls","Edit the highlighted controls to review a rate and consumption sensitivity against August 2026 actuals.");
scenario.getRange("A6:B10").values=[["Control","Value"],["Consumption change",0],["Unit-cost change",0],["Variance alert threshold",0.05],["Scenario notes","Base case is actual August 2026 consumption and invoice cost."]]; header(scenario,"A6:B6"); scenario.getRange("B7:B9").format.fill=amber; scenario.getRange("B7:B9").format.numberFormat="0.0%"; scenario.getRange("B7:B9").dataValidation={rule:{type:"decimal",operator:"between",formula1:-0.5,formula2:0.5}}; widths(scenario,{A:30,B:46});

title(overview,"Energy Ledger executive overview","August 2026 utility invoices. INR totals are local currency. Use slicers in Power BI for interactive site and fuel analysis.");
overview.getRange("A6:H6").values=[["KPI","Actual","Target","Status","KPI","Actual","Target","Status"]]; header(overview,"A6:H6");
overview.getRange("A7:H9").values=[["Invoice cost (INR)",null,600000,null,"Energy (kWh)",null,230000,null],["Emissions (tCO2e)",null,70,null,"Bill-meter variance",null,0.05,null],["High meter anomalies",null,0,null,"Data-quality controls",null,8,null]];
overview.getRange("B7").formulas=[["=ROUND(SUM('Invoice Detail'!$K$7:$K$12),0)"]]; overview.getRange("F7").formulas=[["=ROUND(SUM('Invoice Detail'!$J$7:$J$12),0)"]]; overview.getRange("B8").formulas=[["=ROUND(SUM('Invoice Detail'!$L$7:$L$12)/1000,1)"]]; overview.getRange("F8").values=[[0.0246]]; overview.getRange("B9").values=[[1]]; overview.getRange("F9").values=[[8]];
overview.getRange("D7").formulas=[["=IF(B7<=C7,\"Within target\",\"Above target\")"]]; overview.getRange("H7").formulas=[["=IF(F7<=G7,\"Within target\",\"Above target\")"]]; overview.getRange("D8").formulas=[["=IF(B8<=C8,\"Within target\",\"Above target\")"]]; overview.getRange("H8").formulas=[["=IF(F8<=G8,\"Within target\",\"Above threshold\")"]]; overview.getRange("D9").formulas=[["=IF(B9=0,\"Clear\",\"Review\")"]]; overview.getRange("H9").formulas=[["=IF(F9=G9,\"Complete\",\"Investigate\")"]];
overview.getRange("B7:C9").format.numberFormat="₹#,##0;[Red](₹#,##0);-"; overview.getRange("F7:G7").format.numberFormat="#,#0"; overview.getRange("B8:C8").format.numberFormat="#,##0.0"; overview.getRange("F8:G8").format.numberFormat="0.0%"; overview.getRange("B9:C9").format.numberFormat="#,#0"; overview.getRange("F9:G9").format.numberFormat="#,#0"; overview.getRange("D7:D9").conditionalFormats.add("containsText",{text:"Above",format:{fill:red,font:{color:"#9C0006",bold:true}}}); overview.getRange("H7:H9").conditionalFormats.add("containsText",{text:"Within",format:{fill:green,font:{color:"#006100",bold:true}}});
overview.getRange("A13:D13").values=[["Scenario output","Base actual","Scenario","Change"]]; header(overview,"A13:D13"); overview.getRange("A14:A15").values=[["Energy (kWh)"],["Invoice cost (INR)"]]; overview.getRange("B14").formulas=[["=F7"]]; overview.getRange("C14").formulas=[["=B14*(1+Scenario!$B$7)"]]; overview.getRange("D14").formulas=[["=C14-B14"]]; overview.getRange("B15").formulas=[["=B7"]]; overview.getRange("C15").formulas=[["=B15*(1+Scenario!$B$7)*(1+Scenario!$B$8)"]]; overview.getRange("D15").formulas=[["=C15-B15"]]; overview.getRange("B14:D14").format.numberFormat="#,#0"; overview.getRange("B15:D15").format.numberFormat="₹#,##0;[Red](₹#,##0);-"; widths(overview,{A:26,B:18,C:18,D:18,E:26,F:18,G:18,H:18});
const scenarioChart = overview.charts.add("column", overview.getRange("A13:C15"));
scenarioChart.titleText = "Base and scenario comparison";
scenarioChart.setPosition("A17", "H32");

title(monthly,"Monthly KPI and reporting model","Power BI import grain: site, energy type, billing month, currency. Current source contains one published month.");
monthly.getRange("A6:H6").values=[["Billing month","Site","Energy type","Currency","Invoice lines","Energy kWh","Invoice amount","Emissions tCO2e"]]; header(monthly,"A6:H6");
monthly.getRange("A7:H11").values=[[new Date("2026-08-01"),"Bengaluru HQ","electricity","INR",1,12500,156250,8.85],[new Date("2026-08-01"),"Bengaluru HQ","natural_gas","INR",1,119444.44454,43000,24.1278],[new Date("2026-08-01"),"Bengaluru Distribution Centre","electricity","INR",1,18600,232500,13.1688],[new Date("2026-08-01"),"Bengaluru Distribution Centre","natural_gas","INR",1,69444.4445,25500,14.0278],[new Date("2026-08-01"),"Delhi Sales Office","electricity","INR",2,11000,137500,7.788]]; monthly.getRange("A7:A11").format.numberFormat="mmm-yy"; monthly.getRange("F7:F11").format.numberFormat="#,#0"; monthly.getRange("G7:G11").format.numberFormat="₹#,##0"; monthly.getRange("H7:H11").format.numberFormat="#,##0.0"; widths(monthly,{A:14,B:30,C:16,D:12,E:14,F:16,G:18,H:18});

title(exceptions,"Exceptions and drill-through detail","Prioritize rate, bill-to-meter, and consumption anomaly findings. Detailed resolution workflow belongs in the governed source system.");
exceptions.getRange("A6:H6").values=[["Priority","Finding","Site","Account / meter","Period end","Variance / robust z","Status","Recommended action"]]; header(exceptions,"A6:H6");
exceptions.getRange("A7:H8").values=[["High","Meter consumption anomaly","Bengaluru HQ","MTR-BLR-E1",new Date("2026-09-30"),96.3186,"anomaly_high","Validate reading, operating hours, and meter health before action."],["Review","Bill versus meter","Bengaluru HQ","ELEC-7781",new Date("2026-08-31"),0.0246,"within_5pct_tolerance","Retain as reconciled. Escalate only if threshold changes."]]; exceptions.getRange("E7:E8").format.numberFormat="yyyy-mm-dd"; exceptions.getRange("F7").format.numberFormat="0.0"; exceptions.getRange("F8").format.numberFormat="0.0%"; exceptions.getRange("A7:H7").format.fill=red; exceptions.freezePanes.freezeRows(6); widths(exceptions,{A:12,B:26,C:26,D:20,E:14,F:18,G:24,H:58});

title(quality,"Data quality controls","Latest pipeline quality report. Controls should be refreshed from reports/data_quality_report.md after each model load.");
quality.getRange("A6:C14").values=[["Control","Result","Evidence"],["Required columns","PASS","All four raw sources contain required columns."],["Null threshold","PASS","0 nulls in required fields."],["Duplicate business keys","PASS","6 unique invoice lines."],["Invalid ranges","PASS","Positive quantities and valid intervals."],["Referential integrity","PASS","All invoices resolve to site and factor."],["Freshness","PASS","Latest invoice within 45 days of run date."],["Row reconciliation","PASS","6 raw invoice rows equal 6 fact rows."],["Value reconciliation","PASS","₹594,750 raw equals loaded fact value."]]; header(quality,"A6:C6"); quality.getRange("B7:B14").format.fill=green; widths(quality,{A:28,B:14,C:65});

title(definitions,"Definitions and refresh help","Use this sheet for report definitions, Power BI model loading instructions, and workbook refresh controls.");
definitions.getRange("A6:B15").values=[["Item","Definition"],["Date table","Use a dedicated calendar date table related to billing-end, billing-start, and invoice-date roles. Set billing-end as the active reporting relationship."],["Core measures","Invoice cost, energy kWh, emissions tCO2e, cost per kWh, energy intensity, bill-meter variance, anomaly count, and data-quality pass count."],["Power BI slicers","Billing month, site, energy type, utility account, currency, anomaly status, and reconciliation status."],["Power BI pages","Executive overview, diagnostics, trend, invoice/meter detail, data quality, and definitions/help."],["Excel refresh","Replace Invoice Detail and Monthly KPI query outputs from the SQLite views. Refresh formulas and charts after loading."],["Exception target","Bill-meter variance above 5% is high. Robust z above 3.5 is an anomaly after six prior periods."],["Source system","data/energy_ledger.db views: v_monthly_site_energy_kpis, v_bill_meter_variance, v_meter_anomaly, v_reconciliation_source_to_reporting."],["Power Query","Use the supplied powerbi/sqlite_import_queries.sql as the governed extract definition. Excel’s native SQLite connector or ODBC driver is required for live refresh."]]; header(definitions,"A6:B6"); definitions.getRange("B7:B15").format.wrapText=true; widths(definitions,{A:22,B:100}); definitions.getRange("A6:B15").format.autofitRows();

wb.recalculate();
const check=await wb.inspect({kind:"table",range:"Executive Summary!A6:H15",include:"values,formulas",tableMaxRows:12,tableMaxCols:8}); console.log(check.ndjson);
const errors=await wb.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!",options:{useRegex:true,maxResults:100}}); console.log(errors.ndjson);
await fs.mkdir(new URL("../excel/",import.meta.url).pathname,{recursive:true}); const x=await SpreadsheetFile.exportXlsx(wb); await x.save(out);

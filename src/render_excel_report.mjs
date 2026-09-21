import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";
const input = await FileBlob.load("excel/energy_ledger_management_pack.xlsx");
const wb = await SpreadsheetFile.importXlsx(input);
const image = await wb.render({sheetName:"Executive Summary",range:"A1:H16",scale:1.5});
await fs.mkdir("reports/figures", { recursive: true });
await fs.writeFile("reports/figures/executive_summary.png",new Uint8Array(await image.arrayBuffer()));
const inspect=await wb.inspect({kind:"table",range:"Executive Summary!A6:H15",include:"values,formulas",tableMaxRows:12,tableMaxCols:8});
console.log(inspect.ndjson);

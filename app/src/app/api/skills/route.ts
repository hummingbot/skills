import { getSkillsData } from "@/lib/skills";
import { NextResponse } from "next/server";

export async function GET() {
  const data = await getSkillsData();
  return NextResponse.json(data);
}

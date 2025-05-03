import { NextRequest, NextResponse } from 'next/server';
import { writeFile } from 'fs/promises';
import path from 'path';

export async function POST(req: NextRequest) {
    const data = await req.json();
    const filePath = path.join(process.cwd(), 'custom_cards.json');

    await writeFile(filePath, JSON.stringify(data, null, 2));
    return NextResponse.json({ success: true });
}

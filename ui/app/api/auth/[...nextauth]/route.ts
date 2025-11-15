export async function GET() {
  return Response.json({ error: "Authentication is not configured yet." }, { status: 501 });
}

export const POST = GET;

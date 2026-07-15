import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase-server'

// List / create / delete a user's saved searches (RLS scopes to the caller).
export async function GET() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ ok: false }, { status: 401 })
  const { data } = await supabase.from('saved_searches')
    .select('*').eq('user_id', user.id).order('created_at', { ascending: false })
  return NextResponse.json({ ok: true, searches: data || [] })
}

export async function POST(req: Request) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ ok: false }, { status: 401 })
  const body = await req.json().catch(() => ({}))
  const name = (body.name || 'My search').toString().slice(0, 80)
  const filters = body.filters && typeof body.filters === 'object' ? body.filters : {}
  const { data, error } = await supabase.from('saved_searches')
    .insert({ user_id: user.id, name, filters }).select().single()
  if (error) return NextResponse.json({ ok: false, error: error.message }, { status: 500 })
  return NextResponse.json({ ok: true, search: data })
}

export async function DELETE(req: Request) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ ok: false }, { status: 401 })
  const id = new URL(req.url).searchParams.get('id')
  if (!id) return NextResponse.json({ ok: false, error: 'id required' }, { status: 400 })
  await supabase.from('saved_searches').delete().eq('id', id).eq('user_id', user.id)
  return NextResponse.json({ ok: true })
}

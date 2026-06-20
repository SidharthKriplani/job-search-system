import { NextResponse } from 'next/server'
import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')
  const next = searchParams.get('next') ?? '/dashboard'

  if (!code) {
    return NextResponse.redirect(`${origin}/auth/error`)
  }

  const cookieStore = cookies()
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return cookieStore.getAll() },
        setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          )
        },
      },
    }
  )

  const { data, error } = await supabase.auth.exchangeCodeForSession(code)

  if (error) {
    console.error('Auth callback error:', error)
    return NextResponse.redirect(`${origin}/?error=${encodeURIComponent(error.message)}`)
  }

  // Store Gmail OAuth tokens in gmail_tokens table
  if (data.session?.provider_token && data.session?.provider_refresh_token) {
    const user = data.session.user
    try {
      await supabase.from('gmail_tokens').upsert({
        user_id:       user.id,
        access_token:  data.session.provider_token,
        refresh_token: data.session.provider_refresh_token,
        token_expiry:  data.session.expires_at
          ? new Date(data.session.expires_at * 1000).toISOString()
          : null,
        scope: 'https://www.googleapis.com/auth/gmail.modify',
      }, { onConflict: 'user_id' })

      await supabase.from('user_profiles').upsert({
        user_id:         user.id,
        full_name:       user.user_metadata?.full_name || user.email?.split('@')[0] || '',
        email:           user.email || '',
        gmail_connected: true,
      }, { onConflict: 'user_id', ignoreDuplicates: false })
    } catch (err) {
      console.error('Failed to store Gmail tokens:', err)
    }
  }

  return NextResponse.redirect(`${origin}${next}`)
}

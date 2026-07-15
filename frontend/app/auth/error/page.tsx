export default function AuthError() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 p-4">
      <div className="w-full max-w-md px-8 py-10 bg-white/5 border border-white/10 rounded-2xl text-center">
        <h1 className="text-white font-bold text-lg mb-2">Sign-in didn’t complete</h1>
        <p className="text-slate-400 text-sm mb-6">
          Something interrupted the sign-in. This is usually temporary — please try again.
        </p>
        <a href="/" className="inline-block px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl">
          Back to sign in
        </a>
      </div>
    </div>
  )
}

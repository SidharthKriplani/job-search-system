export const metadata = {
  title: 'Privacy Policy — Job Search System',
  description: 'How Job Search System collects, uses, and protects your data.',
}

const UPDATED = 'July 15, 2026'
const CONTACT = 'sidharthkriplani@gmail.com'
const APP = 'Job Search System'

export default function PrivacyPolicy() {
  return (
    <main className="max-w-2xl mx-auto px-6 py-16 text-slate-800 leading-relaxed">
      <h1 className="text-3xl font-bold mb-2">Privacy Policy</h1>
      <p className="text-sm text-slate-500 mb-8">Last updated: {UPDATED}</p>

      <p className="mb-6">
        {APP} (&quot;the app&quot;, &quot;we&quot;) is a personal job-search assistant that aggregates
        job postings from public sources and, with your explicit consent, from your own email
        job alerts, then filters and ranks them against a profile you provide. This policy explains
        what we collect, why, and the choices you have.
      </p>

      <Section title="Information we collect">
        <ul className="list-disc pl-5 space-y-2">
          <li>
            <strong>Account information.</strong> When you sign in with Google or with an email and
            password, we receive your email address and (for Google) your name and profile basics,
            solely to create and identify your account.
          </li>
          <li>
            <strong>Profile you provide.</strong> Target roles, locations, industries, salary
            preference, and any résumé text you upload. You control this and can edit or clear it at
            any time in Settings.
          </li>
          <li>
            <strong>Gmail data (only if you connect it).</strong> If you choose to connect Gmail, we
            request the <code>gmail.modify</code> scope and read only messages you have labelled as
            job alerts, to extract job postings into your feed. We do not read your general inbox,
            and we do not send, delete, or modify your emails. Connecting Gmail is optional; the app
            works without it.
          </li>
          <li>
            <strong>Activity within the app.</strong> Jobs you save, dismiss, mark applied, or flag
            as &quot;not relevant&quot;, and application-tracker entries you create — used to run the
            product and improve match quality for you.
          </li>
        </ul>
      </Section>

      <Section title="How we use your information">
        <ul className="list-disc pl-5 space-y-2">
          <li>To fetch, filter, rank, and display job postings relevant to your profile.</li>
          <li>To send you an optional daily email digest of new matches and reminders (you can turn this off).</li>
          <li>To operate features you use: the application tracker and referral pipeline.</li>
          <li>To improve matching using your in-app feedback.</li>
        </ul>
        <p className="mt-3">
          We do <strong>not</strong> sell your data, share it with advertisers, or use it for any
          purpose other than operating this app for you. Google user data obtained via the Gmail
          scope is used only to surface job postings to you and is never transferred to third parties
          except as required to run the service (see below).
        </p>
      </Section>

      <Section title="Storage and processing">
        <p>
          Your data is stored in a Supabase (PostgreSQL) database with row-level security, so your
          records are only accessible to your authenticated account. Job aggregation runs on GitHub
          Actions and the app is hosted on Vercel. Email digests, if enabled, are sent via Resend.
          These processors handle data only to provide their part of the service.
        </p>
      </Section>

      <Section title="Google API disclosure">
        <p>
          {APP}&apos;s use and transfer of information received from Google APIs adheres to the{' '}
          <a className="text-indigo-600 underline" href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noreferrer">
            Google API Services User Data Policy
          </a>, including the Limited Use requirements.
        </p>
      </Section>

      <Section title="Your choices and rights">
        <ul className="list-disc pl-5 space-y-2">
          <li>Edit or clear your profile and résumé text anytime in Settings.</li>
          <li>Disconnect Gmail at any time from your Google Account&apos;s third-party access settings; we stop reading your alerts immediately.</li>
          <li>Request deletion of your account and all associated data by emailing us (below); we will remove it promptly.</li>
        </ul>
      </Section>

      <Section title="Data retention">
        <p>
          We keep your profile and tracker data while your account is active. Aggregated job
          postings are refreshed continuously and older postings are pruned automatically. On
          account deletion, your personal data is removed.
        </p>
      </Section>

      <Section title="Contact">
        <p>
          Questions or deletion requests: <a className="text-indigo-600 underline" href={`mailto:${CONTACT}`}>{CONTACT}</a>.
        </p>
      </Section>

      <p className="text-sm text-slate-500 mt-10">
        <a className="text-indigo-600 underline" href="/terms">Terms of Service</a> ·{' '}
        <a className="text-indigo-600 underline" href="/">Home</a>
      </p>
    </main>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold mb-3">{title}</h2>
      <div className="text-slate-700">{children}</div>
    </section>
  )
}

export const metadata = {
  title: 'Terms of Service — Job Search System',
  description: 'The terms governing your use of Job Search System.',
}

const UPDATED = 'July 15, 2026'
const CONTACT = 'sidharthkriplani@gmail.com'
const APP = 'Job Search System'

export default function Terms() {
  return (
    <main className="max-w-2xl mx-auto px-6 py-16 text-slate-800 leading-relaxed">
      <h1 className="text-3xl font-bold mb-2">Terms of Service</h1>
      <p className="text-sm text-slate-500 mb-8">Last updated: {UPDATED}</p>

      <p className="mb-6">
        These terms govern your use of {APP} (&quot;the app&quot;). By creating an account or using
        the app, you agree to them. If you do not agree, please do not use the app.
      </p>

      <Section title="What the app does">
        <p>
          {APP} aggregates publicly available job postings and, if you connect Gmail, job postings
          from your own labelled email alerts. It filters and ranks them against a profile you
          provide and helps you track applications. It is a personal productivity tool, provided for
          your individual job search.
        </p>
      </Section>

      <Section title="Your account">
        <ul className="list-disc pl-5 space-y-2">
          <li>You are responsible for the accuracy of the profile information you provide and for activity under your account.</li>
          <li>You must not use the app for any unlawful purpose, or attempt to disrupt, overload, or reverse-engineer the service.</li>
          <li>You must not use the app to scrape, resell, or redistribute job data in violation of any source&apos;s terms.</li>
        </ul>
      </Section>

      <Section title="Job data accuracy">
        <p>
          Job postings, salary figures, and other details are aggregated from third-party sources
          and may be incomplete, out of date, or inaccurate. We do not guarantee the availability,
          accuracy, or outcome of any posting. Always verify details on the employer&apos;s official
          site before applying. The app does not submit applications on your behalf.
        </p>
      </Section>

      <Section title="Availability">
        <p>
          The app is provided on an &quot;as is&quot; and &quot;as available&quot; basis, without
          warranties of any kind. It may be modified, interrupted, or discontinued at any time. We
          are not liable for any loss arising from your use of, or inability to use, the app,
          including missed opportunities or reliance on aggregated data.
        </p>
      </Section>

      <Section title="Third-party services">
        <p>
          The app links to and depends on third-party services (job boards, Google, Supabase,
          Vercel, Resend). Your use of those services is subject to their own terms. We are not
          responsible for third-party content or availability.
        </p>
      </Section>

      <Section title="Termination">
        <p>
          You may stop using the app and request account deletion at any time. We may suspend or
          terminate access that violates these terms.
        </p>
      </Section>

      <Section title="Changes">
        <p>
          We may update these terms; the &quot;last updated&quot; date reflects the latest version.
          Continued use after changes constitutes acceptance.
        </p>
      </Section>

      <Section title="Contact">
        <p>
          Questions: <a className="text-indigo-600 underline" href={`mailto:${CONTACT}`}>{CONTACT}</a>.
        </p>
      </Section>

      <p className="text-sm text-slate-500 mt-10">
        <a className="text-indigo-600 underline" href="/privacy">Privacy Policy</a> ·{' '}
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

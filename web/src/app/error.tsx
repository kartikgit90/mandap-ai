"use client";

// Shown instead of a blank "Application error" page, so problems are easy to report.
export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main className="min-h-screen flex items-center justify-center px-4">
      <div className="card max-w-lg p-6">
        <h1 className="font-serif text-3xl font-bold">Something went wrong</h1>
        <p className="mt-2 text-sm text-muted">Please send this message to the team:</p>
        <pre className="mt-3 whitespace-pre-wrap break-words rounded-lg bg-cream p-3 text-xs">{error.message || String(error)}</pre>
        <div className="mt-4 flex gap-2">
          <button className="btn-primary" onClick={() => reset()}>Try again</button>
          <button className="btn-ghost" onClick={() => window.location.reload()}>Reload page</button>
        </div>
      </div>
    </main>
  );
}

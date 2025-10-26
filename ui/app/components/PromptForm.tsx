'use client';

import { useState } from 'react';
import styles from './PromptForm.module.css';

export default function PromptForm() {
  const [prompt, setPrompt] = useState('');
  const [result, setResult] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setResult('');

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/prompt`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt: prompt }),
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.statusText}`);
      }

      const data = await response.json();
      setResult(JSON.stringify(data, null, 2));

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <form onSubmit={handleSubmit} className={styles.form}>
        <textarea
          className={styles.textarea}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter your orchestration prompt..."
          required
          disabled={isLoading}
        />
        <button type="submit" className={styles.button} disabled={isLoading}>
          {isLoading ? 'Orchestrating...' : 'Submit'}
        </button>
      </form>

      {error && <div className={styles.error}>Error: {error}</div>}
      
      {result && (
        <div className={styles.resultContainer}>
          <h3>Result:</h3>
          <pre className={styles.resultPre}><code>{result}</code></pre>
        </div>
      )}
    </div>
  );
}

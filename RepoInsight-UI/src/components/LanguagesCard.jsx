import React from 'react'
import { Card, CardSection } from './UI'
import { LANGUAGES } from '../constants/sampling'

const LANGUAGE_COLORS = {
  JavaScript: '#f1e05a',
  TypeScript: '#3178c6',
  Python: '#3572A5',
  Java: '#b07219',
  Go: '#00ADD8',
  Rust: '#dea584',
  C: '#555555',
  'C++': '#f34b7d',
  'C#': '#178600',
  PHP: '#4F5D95',
  Ruby: '#701516',
  Swift: '#F05138',
  Kotlin: '#A97BFF',
  HTML: '#e34c26',
  CSS: '#563d7c',
  CoffeeScript: '#244776',
  Shell: '#89e051',
}

export default function LanguagesCard({ data }) {
  const languageData = data?.languages ?? {}

  const entries = Array.isArray(languageData.languages)
    ? [...languageData.languages].sort((a, b) => b.bytes - a.bytes)
    : []

  const totalBytes = languageData.total_bytes ?? 0

  return (
    <Card>
      <CardSection title="languages" finePrint={`top ${LANGUAGES} languages by bytes`} />

      {entries.length === 0 ? (
        <div
          style={{
            color: 'var(--text-muted)',
            fontSize: 13,
          }}
        >
          No language data available
        </div>
      ) : (
        <>
          <div
            style={{
              display: 'flex',
              height: 8,
              borderRadius: 4,
              overflow: 'hidden',
              background: 'var(--border)',
              marginBottom: 18,
            }}
          >
            {entries.map(({ language, percentage }) => (
              <div
                key={language}
                title={`${language}: ${percentage.toFixed(2)}%`}
                style={{
                  width: `${percentage}%`,
                  background:
                    LANGUAGE_COLORS[language] ?? 'var(--blue)',
                  minWidth: percentage > 0 ? 2 : 0,
                }}
              />
            ))}
          </div>

          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
            }}
          >
            {entries.slice(0, 8).map(
              ({ language, bytes, percentage }) => (
                <div key={language}>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: 4,
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 7,
                        minWidth: 0,
                      }}
                    >
                      <span
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: '50%',
                          flexShrink: 0,
                          background:
                            LANGUAGE_COLORS[language] ?? 'var(--blue)',
                        }}
                      />

                      <span
                        style={{
                          fontSize: 12,
                          color: 'var(--text-secondary)',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {language}
                      </span>
                    </div>

                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 11,
                        color: 'var(--text-muted)',
                        flexShrink: 0,
                        marginLeft: 12,
                      }}
                    >
                      {percentage.toFixed(2)}%
                    </span>
                  </div>

                  <div
                    style={{
                      height: 4,
                      background: 'var(--border)',
                      borderRadius: 2,
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${percentage}%`,
                        height: '100%',
                        background:
                          LANGUAGE_COLORS[language] ?? 'var(--blue)',
                        borderRadius: 2,
                      }}
                    />
                  </div>
                </div>
              )
            )}
          </div>

          <div
            style={{
              marginTop: 16,
              paddingTop: 12,
              borderTop: '1px solid var(--border)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span
              style={{
                fontSize: 11,
                color: 'var(--text-muted)',
              }}
            >
              Total analyzed
            </span>

            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                color: 'var(--text-secondary)',
              }}
            >
              {totalBytes.toLocaleString()} bytes
            </span>
          </div>
        </>
      )}
    </Card>
  )
}

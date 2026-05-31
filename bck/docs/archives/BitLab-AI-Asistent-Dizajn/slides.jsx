// BitLab AI Asistent — slide components
// All sizes follow TYPE_SCALE and SPACING constants.

const TYPE_SCALE = {
  display: 200,
  hero: 120,
  title: 64,
  subtitle: 44,
  body: 34,
  small: 28,
  micro: 22,
};

const SPACING = {
  paddingTop: 100,
  paddingBottom: 80,
  paddingX: 110,
  titleGap: 52,
  itemGap: 28,
};

const C = {
  orange: '#fb6d3b',
  orangeHover: '#ea5c2a',
  orangeDeep: '#e0511f',
  peach: '#fff5f0',
  navy: '#1a1a2e',
  navy2: '#2a2a3e',
  text: '#222',
  text2: '#666',
  muted: '#999',
  green: '#27ae60',
  red: '#e74c3c',
  border: '#e6e6e6',
  borderSoft: '#f0f0f0',
  bgSoft: '#f9f9f9',
  bgSofter: '#fafafa',
};

// --- Shared bits ---------------------------------------------------------

function SlideFrame({ children, bg = '#ffffff', style = {}, padded = true }) {
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        background: bg,
        boxSizing: 'border-box',
        padding: padded
          ? `${SPACING.paddingTop}px ${SPACING.paddingX}px ${SPACING.paddingBottom}px`
          : 0,
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        fontFamily: 'Inter, -apple-system, sans-serif',
        color: C.text,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

function SlideMeta({ index, total, color = C.muted }) {
  return (
    <div
      style={{
        position: 'absolute',
        bottom: 36,
        left: SPACING.paddingX,
        right: SPACING.paddingX,
        display: 'flex',
        justifyContent: 'space-between',
        fontFamily: 'JetBrains Mono, ui-monospace, monospace',
        fontSize: TYPE_SCALE.micro,
        color,
        letterSpacing: '0.02em',
      }}
    >
      <span>BitLab AI Asistent</span>
      <span>
        {String(index).padStart(2, '0')} / {String(total).padStart(2, '0')}
      </span>
    </div>
  );
}

function Eyebrow({ children, color = C.orange }) {
  return (
    <div
      style={{
        fontFamily: 'JetBrains Mono, ui-monospace, monospace',
        fontSize: TYPE_SCALE.micro,
        textTransform: 'uppercase',
        letterSpacing: '0.18em',
        color,
        fontWeight: 500,
      }}
    >
      {children}
    </div>
  );
}

function Title({ children, color = C.navy, size = TYPE_SCALE.title }) {
  return (
    <h1
      style={{
        fontSize: size,
        fontWeight: 600,
        lineHeight: 1.05,
        letterSpacing: '-0.025em',
        color,
        margin: 0,
        textWrap: 'balance',
      }}
    >
      {children}
    </h1>
  );
}

// --- 01: Cover ----------------------------------------------------------

function CoverSlide({ index, total }) {
  return (
    <SlideFrame bg={C.peach} padded={false}>
      <div
        style={{
          flex: 1,
          display: 'grid',
          gridTemplateColumns: '1.1fr 0.9fr',
          alignItems: 'stretch',
        }}
      >
        {/* Left: identity + statement */}
        <div
          style={{
            padding: `${SPACING.paddingTop}px ${SPACING.paddingX}px ${SPACING.paddingBottom}px`,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <img
              src="bitlab-logo.png"
              alt="BitLab"
              style={{ height: 64, width: 'auto', display: 'block' }}
            />
            <span
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: TYPE_SCALE.micro,
                color: C.text2,
                marginLeft: 'auto',
              }}
            >
              webshop.bitlab.rs
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 36 }}>
            <Eyebrow>Pitch · maj 2026</Eyebrow>
            <Title size={140} color={C.navy}>
              AI Asistent
              <span style={{ color: C.orange }}>.</span>
            </Title>
            <p
              style={{
                fontSize: TYPE_SCALE.subtitle,
                lineHeight: 1.25,
                color: C.text,
                margin: 0,
                maxWidth: 720,
                fontWeight: 400,
              }}
            >
              Asistent za chat, glas i e-mail nad cijelim
              <br />
              katalogom — spreman za pokretanje.
            </p>
          </div>

          <div
            style={{
              display: 'flex',
              gap: 48,
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: TYPE_SCALE.micro,
              color: C.text2,
            }}
          >
            <span>BitLab d.o.o.</span>
            <span>Banja Luka</span>
            <span>2026</span>
          </div>
        </div>

        {/* Right: peach panel with orange detail */}
        <div
          style={{
            background: '#ffe8db',
            position: 'relative',
            overflow: 'hidden',
            display: 'flex',
            alignItems: 'flex-end',
            justifyContent: 'flex-end',
          }}
        >
          {/* monogram block */}
          <div
            style={{
              position: 'absolute',
              top: 80,
              right: 80,
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: TYPE_SCALE.micro,
              color: C.navy,
              opacity: 0.6,
              textAlign: 'right',
              lineHeight: 1.6,
            }}
          >
            chat<br />voice<br />e-mail
          </div>

          {/* Stacked huge numerals */}
          <div
            style={{
              position: 'absolute',
              right: -40,
              bottom: -60,
              fontSize: 520,
              fontWeight: 700,
              fontFamily: 'Inter, sans-serif',
              letterSpacing: '-0.06em',
              lineHeight: 0.85,
              color: C.orange,
              textAlign: 'right',
            }}
          >
            5278
          </div>
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: 60,
              transform: 'translateY(-50%) rotate(-90deg)',
              transformOrigin: 'left center',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: TYPE_SCALE.micro,
              color: C.navy,
              letterSpacing: '0.3em',
              textTransform: 'uppercase',
            }}
          >
            Proizvoda u realnom vremenu
          </div>
        </div>
      </div>
    </SlideFrame>
  );
}

// --- 02: Stvarnost u brojkama (context) -------------------------------

function ContextSlide({ index, total }) {
  return (
    <SlideFrame bg="#ffffff">
      <Eyebrow>01 · Polazište</Eyebrow>
      <div style={{ height: SPACING.titleGap }} />
      <Title>Polazimo od stvarnih brojeva.</Title>

      <div style={{ height: 80 }} />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 0,
          borderTop: `1px solid ${C.border}`,
          borderBottom: `1px solid ${C.border}`,
        }}
      >
        {[
          { n: '5.278', l: 'proizvoda u katalogu', s: 'svaki sa cijenom, slikom i dostupnoš\u0107u' },
          { n: '3', l: 'kanala iz iste baze', s: 'chat, glas, e-mail' },
          { n: '24/7', l: 'dostupnost', s: 'i van radnog vremena' },
        ].map((stat, i) => (
          <div
            key={i}
            style={{
              padding: '56px 40px',
              borderLeft: i === 0 ? 'none' : `1px solid ${C.border}`,
              display: 'flex',
              flexDirection: 'column',
              gap: 16,
            }}
          >
            <div
              style={{
                fontSize: TYPE_SCALE.hero,
                fontWeight: 700,
                color: C.navy,
                letterSpacing: '-0.04em',
                lineHeight: 1,
              }}
            >
              {stat.n}
            </div>
            <div
              style={{
                fontSize: TYPE_SCALE.body,
                color: C.text,
                fontWeight: 500,
              }}
              dangerouslySetInnerHTML={{ __html: stat.l }}
            />
            <div
              style={{
                fontSize: TYPE_SCALE.small,
                color: C.text2,
                fontWeight: 400,
              }}
              dangerouslySetInnerHTML={{ __html: stat.s }}
            />
          </div>
        ))}
      </div>

      <div style={{ height: 60 }} />

      <p
        style={{
          fontSize: TYPE_SCALE.small,
          color: C.text2,
          maxWidth: 1100,
          lineHeight: 1.45,
          margin: 0,
        }}
      >
        Webshop sa hiljadama proizvoda i dnevnim upitima na tri kanala.
        Svaki kanal je prilika — ili pad u red čekanja.
      </p>

      <SlideMeta index={index} total={total} />
    </SlideFrame>
  );
}

// --- 03: Tri kanala, jedna baza znanja --------------------------------

function ChannelsSlide({ index, total }) {
  const channels = [
    {
      tag: 'chat',
      title: 'Widget na sajtu',
      ex: '\u201eImate li SSD 1TB do 400 KM?\u201c',
      ans: 'Lista 3 proizvoda · cijene · linkovi → webshop',
    },
    {
      tag: 'glas',
      title: 'Voice na materinjem',
      ex: '\u201eTra\u017eim laptop do 1500 KM, gaming.\u201c',
      ans: 'Odgovara glasom · native BCS izgovor cijena',
    },
    {
      tag: 'e-mail',
      title: 'Auto-reply za 30s',
      ex: 'Upit za firmu, JIB 4401234567891',
      ans: 'Profesionalan reply · eskalacija na prodaju kad treba',
    },
  ];

  return (
    <SlideFrame bg="#ffffff">
      <Eyebrow>02 · Proizvod</Eyebrow>
      <div style={{ height: SPACING.titleGap }} />
      <Title>Tri kanala, jedna baza znanja.</Title>

      <div style={{ height: 64 }} />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 24,
          flex: 1,
        }}
      >
        {channels.map((ch, i) => (
          <div
            key={i}
            style={{
              border: `1px solid ${C.border}`,
              borderRadius: 12,
              padding: '40px 36px',
              display: 'flex',
              flexDirection: 'column',
              gap: 24,
              background: '#fff',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 14,
              }}
            >
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: 2,
                  background: C.orange,
                }}
              />
              <span
                style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: TYPE_SCALE.micro,
                  textTransform: 'uppercase',
                  letterSpacing: '0.2em',
                  color: C.text2,
                }}
              >
                {ch.tag}
              </span>
            </div>
            <div
              style={{
                fontSize: TYPE_SCALE.subtitle,
                fontWeight: 600,
                color: C.navy,
                letterSpacing: '-0.02em',
                lineHeight: 1.1,
              }}
            >
              {ch.title}
            </div>

            <div
              style={{
                marginTop: 'auto',
                paddingTop: 28,
                borderTop: `1px dashed ${C.border}`,
                display: 'flex',
                flexDirection: 'column',
                gap: 16,
              }}
            >
              <div
                style={{
                  fontSize: TYPE_SCALE.small,
                  color: C.text,
                  fontStyle: 'italic',
                  lineHeight: 1.35,
                }}
                dangerouslySetInnerHTML={{ __html: ch.ex }}
              />
              <div
                style={{
                  fontSize: TYPE_SCALE.small,
                  color: C.text2,
                  lineHeight: 1.35,
                }}
                dangerouslySetInnerHTML={{ __html: ch.ans }}
              />
            </div>
          </div>
        ))}
      </div>

      <div style={{ height: 36 }} />

      <div
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: TYPE_SCALE.micro,
          color: C.text2,
          display: 'flex',
          alignItems: 'center',
          gap: 16,
        }}
      >
        <span>katalog · FAQ · B2B pravila</span>
        <span style={{ color: C.muted }}>→</span>
        <span>jedan izvor istine</span>
      </div>

      <SlideMeta index={index} total={total} />
    </SlideFrame>
  );
}

// --- 04: Storyboard demo ---------------------------------------------

function ChatMock() {
  return (
    <div
      style={{
        background: '#fff',
        borderRadius: 12,
        border: `1px solid ${C.border}`,
        padding: 18,
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        height: '100%',
        boxShadow: '0 1px 0 rgba(26,26,46,0.04)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ width: 10, height: 10, borderRadius: 99, background: C.orange }} />
        <span style={{ fontSize: 16, fontWeight: 600, color: C.navy, whiteSpace: 'nowrap' }}>BitLab AI</span>
        <span style={{ fontSize: 13, color: C.green, marginLeft: 'auto', whiteSpace: 'nowrap' }}>● online</span>
      </div>
      <div
        style={{
          alignSelf: 'flex-end',
          background: C.orange,
          color: '#fff',
          padding: '10px 14px',
          borderRadius: '14px 14px 4px 14px',
          fontSize: 16,
          maxWidth: '80%',
        }}
      >
        Imate li SSD 1TB do 400 KM?
      </div>
      <div
        style={{
          background: '#f4f4f6',
          padding: '10px 14px',
          borderRadius: '14px 14px 14px 4px',
          fontSize: 15,
          color: C.text,
          lineHeight: 1.4,
        }}
      >
        Da. Imam 3 modela:<br />
        <span style={{ fontWeight: 600 }}>Patriot P210 1TB</span> — 369 KM<br />
        <span style={{ fontWeight: 600 }}>Kingston A400</span> — 389 KM
      </div>
    </div>
  );
}

function VoiceMock() {
  return (
    <div
      style={{
        background: C.navy,
        borderRadius: 12,
        padding: 24,
        display: 'flex',
        flexDirection: 'column',
        gap: 18,
        height: '100%',
        color: '#fff',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div
          style={{
            width: 12,
            height: 12,
            borderRadius: 99,
            background: C.orange,
            boxShadow: `0 0 0 6px rgba(251,109,59,0.2)`,
          }}
        />
        <span style={{ fontSize: 14, fontWeight: 500, letterSpacing: '0.1em', textTransform: 'uppercase', opacity: 0.7 }}>
          slušam...
        </span>
      </div>

      {/* waveform */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, height: 56 }}>
        {[18, 32, 48, 26, 52, 38, 22, 44, 30, 50, 36, 24, 42, 28, 46, 34, 20].map((h, i) => (
          <div
            key={i}
            style={{
              width: 4,
              height: h,
              background: i % 3 === 0 ? C.orange : '#fff',
              opacity: i % 3 === 0 ? 1 : 0.5,
              borderRadius: 2,
            }}
          />
        ))}
      </div>

      <div style={{ fontSize: 17, fontStyle: 'italic', lineHeight: 1.4, opacity: 0.95 }}>
        „Tražim laptop do hiljadu petsto maraka, za gaming.“
      </div>

      <div
        style={{
          marginTop: 'auto',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 13,
          color: C.orange,
          opacity: 0.85,
        }}
      >
        bcs · native voice
      </div>
    </div>
  );
}

function EmailMock() {
  return (
    <div
      style={{
        background: '#fff',
        borderRadius: 12,
        border: `1px solid ${C.border}`,
        padding: 22,
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
        height: '100%',
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 13,
        color: C.text,
        lineHeight: 1.55,
      }}
    >
      <div style={{ color: C.muted, fontSize: 12 }}>From: prodaja@bitlab.rs</div>
      <div style={{ color: C.muted, fontSize: 12 }}>Subject: Re: Ponuda za 5 SSD-ova</div>
      <div style={{ height: 1, background: C.borderSoft }} />
      <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 15, color: C.text }}>
        Poštovani,<br /><br />
        zahvaljujemo na upitu. Pošto se radi o B2B narudžbi sa JIB-om,
        proslijedio sam zahtjev našem prodajnom timu — javiće Vam se u toku dana.
      </div>
      <div
        style={{
          marginTop: 'auto',
          padding: '10px 12px',
          background: '#f0fbf3',
          color: C.green,
          borderRadius: 6,
          fontSize: 12,
        }}
      >
        ✓ auto-reply · 28s · eskalirano prodaji
      </div>
    </div>
  );
}

function DemoSlide({ index, total }) {
  return (
    <SlideFrame bg={C.bgSofter}>
      <Eyebrow>03 · 90-sekundni demo</Eyebrow>
      <div style={{ height: SPACING.titleGap }} />
      <Title>Jedan minut, tri pitanja.</Title>

      <div style={{ height: 56 }} />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr',
          gap: 28,
          flex: 1,
          alignItems: 'stretch',
        }}
      >
        {[
          { mock: <ChatMock />, label: 'chat', t: '00:00 — 00:30' },
          { mock: <VoiceMock />, label: 'voice', t: '00:30 — 00:50' },
          { mock: <EmailMock />, label: 'e-mail', t: '00:50 — 01:30' },
        ].map((s, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ flex: 1, minHeight: 0 }}>{s.mock}</div>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: TYPE_SCALE.micro,
                color: C.text2,
              }}
            >
              <span>{s.label}</span>
              <span dangerouslySetInnerHTML={{ __html: s.t }} />
            </div>
          </div>
        ))}
      </div>

      <SlideMeta index={index} total={total} />
    </SlideFrame>
  );
}

// --- 05: Differentiator (audit checklist) ---------------------------

function DifferentiatorSlide({ index, total }) {
  const rows = [
    { label: 'Skala', them: '10\u201350 fake proizvoda', us: '5.278 stvarnih iz kataloga' },
    { label: 'Kanali', them: 'samo chat', us: 'chat, glas, e-mail' },
    { label: 'Jezik', them: 'engleski + auto-prevod', us: 'BCS-native, latinica' },
    { label: 'Hosting', them: 'tu\u0111i cloud', us: 've\u0107 BitLab VPS' },
    { label: 'E-mail', them: '\u2014', us: 'auto-reply sa eskalacijom' },
    { label: 'Kvalitet', them: '"izgleda da radi"', us: 'eval suite · ciljano 17/18' },
    { label: 'Sigurnost', them: 'klju\u010dovi u browseru', us: 'klju\u010dovi samo na backend-u' },
    { label: 'Cijena rada', them: 'nepoznata', us: '~30 KM mjese\u010dno' },
  ];

  return (
    <SlideFrame bg="#ffffff">
      <Eyebrow>04 · Pristup</Eyebrow>
      <div style={{ height: SPACING.titleGap }} />
      <Title>Šta je odlučeno drugačije.</Title>

      <div style={{ height: 56 }} />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '180px 1fr 1fr',
          gap: 0,
          fontSize: TYPE_SCALE.small,
          flex: 1,
        }}
      >
        {/* Header */}
        <div />
        <div
          style={{
            padding: '14px 28px',
            color: C.muted,
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: TYPE_SCALE.micro,
            textTransform: 'uppercase',
            letterSpacing: '0.18em',
            borderBottom: `1px solid ${C.border}`,
          }}
        >
          tipični pristup
        </div>
        <div
          style={{
            padding: '14px 28px',
            color: C.orange,
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: TYPE_SCALE.micro,
            textTransform: 'uppercase',
            letterSpacing: '0.18em',
            borderBottom: `2px solid ${C.orange}`,
            fontWeight: 600,
          }}
        >
          ovaj projekat
        </div>

        {rows.map((r, i) => (
          <React.Fragment key={i}>
            <div
              style={{
                padding: '18px 0',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: TYPE_SCALE.micro,
                color: C.text2,
                borderBottom: i === rows.length - 1 ? 'none' : `1px solid ${C.borderSoft}`,
                display: 'flex',
                alignItems: 'center',
                letterSpacing: '0.05em',
              }}
            >
              {String(i + 1).padStart(2, '0')} · {r.label}
            </div>
            <div
              style={{
                padding: '18px 28px',
                color: C.text2,
                borderBottom: i === rows.length - 1 ? 'none' : `1px solid ${C.borderSoft}`,
                fontSize: TYPE_SCALE.small,
              }}
              dangerouslySetInnerHTML={{ __html: r.them }}
            />
            <div
              style={{
                padding: '18px 28px',
                color: C.navy,
                fontWeight: 500,
                borderBottom: i === rows.length - 1 ? 'none' : `1px solid ${C.borderSoft}`,
                fontSize: TYPE_SCALE.small,
                display: 'flex',
                alignItems: 'center',
                gap: 14,
              }}
            >
              <span style={{ color: C.green, fontSize: 22 }}>✓</span>
              <span dangerouslySetInnerHTML={{ __html: r.us }} />
            </div>
          </React.Fragment>
        ))}
      </div>

      <SlideMeta index={index} total={total} />
    </SlideFrame>
  );
}

// --- 06: Mjereno, ne tvrdjeno ---------------------------------------

function EvalSlide({ index, total }) {
  return (
    <SlideFrame bg={C.navy} style={{ color: '#fff' }}>
      <Eyebrow color={C.orange}>05 · Provjera</Eyebrow>
      <div style={{ height: SPACING.titleGap }} />
      <Title color="#fff">Mjereno, a ne samo tvrđeno.</Title>

      <div style={{ height: 70 }} />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1.2fr 1fr',
          gap: 60,
          flex: 1,
          alignItems: 'center',
        }}
      >
        {/* Left: huge number + verdict */}
        <div>
          <div
            style={{
              fontSize: 320,
              fontWeight: 700,
              lineHeight: 0.88,
              letterSpacing: '-0.05em',
              color: '#fff',
              fontFamily: 'Inter, sans-serif',
            }}
          >
            17<span style={{ color: C.orange }}>/</span>18
          </div>
          <div
            style={{
              fontSize: TYPE_SCALE.body,
              color: 'rgba(255,255,255,0.75)',
              marginTop: 24,
              maxWidth: 580,
              lineHeight: 1.4,
            }}
          >
            Ciljani skor na eval setu od 18 stvarnih BCS pitanja —
            cijene, dostupnost, dostava, B2B procedura.
          </div>
        </div>

        {/* Right: terminal-ish list */}
        <div
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 8,
            padding: '28px 32px',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: TYPE_SCALE.micro,
            lineHeight: 2.1,
            color: 'rgba(255,255,255,0.85)',
          }}
        >
          <div style={{ color: 'rgba(255,255,255,0.4)', marginBottom: 8 }}>
            $ python evals/run.py
          </div>
          {[
            ['SSD pretraga po cijeni', true],
            ['SKU lookup', true],
            ['Parafraza "brzi disk" \u2192 SSD', true],
            ['Halucinacija cijene', true],
            ['Dostava Mostar — FAQ', true],
            ['B2B JIB — eskalacija', true],
            ['Out-of-stock kontekst', false],
          ].map(([label, ok], i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <span style={{ color: ok ? C.green : C.red, width: 20 }}>
                {ok ? '\u2713' : '\u2717'}
              </span>
              <span dangerouslySetInnerHTML={{ __html: label }} />
            </div>
          ))}
          <div
            style={{
              marginTop: 16,
              paddingTop: 16,
              borderTop: '1px solid rgba(255,255,255,0.1)',
              color: C.orange,
            }}
          >
            ── passed: 17/18 · 94%
          </div>
        </div>
      </div>

      <SlideMeta index={index} total={total} color="rgba(255,255,255,0.5)" />
    </SlideFrame>
  );
}

// --- 07: Tech stack ------------------------------------------------

function StackSlide({ index, total }) {
  return (
    <SlideFrame bg="#ffffff">
      <Eyebrow>06 · Kako je sastavljeno</Eyebrow>
      <div style={{ height: SPACING.titleGap }} />
      <Title>Sve lokalno, bez vendor lock-in-a.</Title>

      <div style={{ height: 80 }} />

      {/* Pipeline diagram */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 0,
          alignItems: 'stretch',
        }}
      >
        {[
          { tag: 'Korisnik', body: 'chat, glas\nili e-mail', color: C.navy },
          { tag: '3 kanala', body: 'jedan ulaz\nu sistem', color: C.navy },
          { tag: 'AI mozak', body: 'odlu\u010dujue \u0161ta\nradi i kako', color: C.orange },
          { tag: 'Katalog + FAQ', body: '5.278 proizvoda\nhibridna pretraga', color: C.navy },
        ].map((node, i, arr) => (
          <div
            key={i}
            style={{
              padding: '40px 28px',
              borderTop: `2px solid ${node.color}`,
              borderRight: i === arr.length - 1 ? 'none' : `1px solid ${C.borderSoft}`,
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
              position: 'relative',
            }}
          >
            <div
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: TYPE_SCALE.micro,
                color: node.color,
                textTransform: 'uppercase',
                letterSpacing: '0.18em',
              }}
            >
              {String(i + 1).padStart(2, '0')}
            </div>
            <div
              style={{
                fontSize: TYPE_SCALE.subtitle,
                fontWeight: 600,
                color: C.navy,
                letterSpacing: '-0.02em',
                lineHeight: 1.05,
              }}
            >
              {node.tag}
            </div>
            <div
              style={{
                fontSize: TYPE_SCALE.small,
                color: C.text2,
                whiteSpace: 'pre-line',
                lineHeight: 1.35,
              }}
            >
              {node.body}
            </div>
            {i < arr.length - 1 && (
              <div
                style={{
                  position: 'absolute',
                  right: -10,
                  top: 32,
                  fontSize: 28,
                  color: C.muted,
                  background: '#fff',
                  width: 20,
                  textAlign: 'center',
                }}
              >
                →
              </div>
            )}
          </div>
        ))}
      </div>

      <div style={{ height: 64 }} />

      {/* Components row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 28,
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: TYPE_SCALE.micro,
          color: C.text2,
        }}
      >
        {[
          ['AI', 'frontier modeli\nza odluke i e-mail'],
          ['Pretraga', 'lokalna vektorska\n+ keyword fusion'],
          ['Voice', 'lokalni STT\n+ neuralni TTS'],
          ['Automation', 'n8n workflows\nlokalno hostovani'],
        ].map(([k, v], i) => (
          <div
            key={i}
            style={{ display: 'flex', flexDirection: 'column', gap: 8, lineHeight: 1.5 }}
          >
            <span style={{ color: C.orange, textTransform: 'uppercase', letterSpacing: '0.2em' }}>
              {k}
            </span>
            <span style={{ whiteSpace: 'pre-line' }}>{v}</span>
          </div>
        ))}
      </div>

      <SlideMeta index={index} total={total} />
    </SlideFrame>
  );
}

// --- 08: Sigurnost --------------------------------------------------

function SecuritySlide({ index, total }) {
  return (
    <SlideFrame bg={C.peach}>
      <Eyebrow>07 · Sigurnost i privatnost</Eyebrow>
      <div style={{ height: SPACING.titleGap }} />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1.2fr 1fr',
          gap: 100,
          flex: 1,
          alignItems: 'center',
        }}
      >
        <div>
          <Title size={92}>
            Vaš server.<br />
            Vaši podaci.<br />
            <span style={{ color: C.orange }}>Vaš AI.</span>
          </Title>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
          {[
            ['VPS BitLab-a', 'Sve komponente rade na vašoj infrastrukturi.'],
            ['Bez trećih lica', 'Nema ngrok-a, tunela ni eksternih webhook-ova.'],
            ['Ključevi u backend-u', 'Nikada nisu izloženi u browseru.'],
            ['Audit prošao', 'Nalazi adresirani prije produkcije.'],
          ].map(([h, b], i) => (
            <div key={i} style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>
              <div
                style={{
                  width: 8,
                  height: 8,
                  background: C.orange,
                  borderRadius: 2,
                  marginTop: 18,
                  flexShrink: 0,
                }}
              />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div
                  style={{
                    fontSize: TYPE_SCALE.body,
                    fontWeight: 600,
                    color: C.navy,
                    letterSpacing: '-0.01em',
                  }}
                >
                  {h}
                </div>
                <div
                  style={{ fontSize: TYPE_SCALE.small, color: C.text2, lineHeight: 1.4 }}
                  dangerouslySetInnerHTML={{ __html: b }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <SlideMeta index={index} total={total} />
    </SlideFrame>
  );
}

// --- 09: Tro\u0161ak rada -----------------------------------------------

function CostSlide({ index, total }) {
  return (
    <SlideFrame bg="#ffffff">
      <Eyebrow>08 · Trošak rada</Eyebrow>
      <div style={{ height: SPACING.titleGap }} />
      <Title>Manje od jedne narudžbe SSD-a, mjesečno.</Title>

      <div style={{ height: 80 }} />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1.2fr',
          gap: 80,
          flex: 1,
          alignItems: 'center',
        }}
      >
        {/* Big number */}
        <div>
          <div
            style={{
              fontSize: 280,
              fontWeight: 700,
              lineHeight: 0.85,
              letterSpacing: '-0.05em',
              color: C.navy,
              display: 'flex',
              alignItems: 'baseline',
              gap: 16,
            }}
          >
            ~30
            <span style={{ fontSize: 80, color: C.orange, fontWeight: 600 }}>KM</span>
          </div>
          <div
            style={{
              fontSize: TYPE_SCALE.body,
              color: C.text2,
              marginTop: 24,
              fontWeight: 400,
            }}
          >
            mjesečno, za realan saobraćaj.
          </div>
        </div>

        {/* Breakdown */}
        <div
          style={{
            borderTop: `1px solid ${C.border}`,
            borderBottom: `1px solid ${C.border}`,
          }}
        >
          {[
            { l: 'AI tokeni', v: '~$15\u201325', n: 'API trošak po realnom saobraćaju' },
            { l: 'Hosting', v: '$0', n: 'već postojeći BitLab VPS' },
            { l: 'Voice, pretraga, automation', v: '$0', n: 'sve lokalno / open source' },
            { l: 'Vendor lock-in', v: '0', n: 'nijedna zavisnost izvan vaše kontrole' },
          ].map((row, i, arr) => (
            <div
              key={i}
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr auto',
                padding: '22px 0',
                borderBottom: i === arr.length - 1 ? 'none' : `1px solid ${C.borderSoft}`,
                gap: 32,
                alignItems: 'baseline',
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: TYPE_SCALE.small,
                    fontWeight: 500,
                    color: C.navy,
                    marginBottom: 4,
                  }}
                >
                  {row.l}
                </div>
                <div
                  style={{ fontSize: TYPE_SCALE.micro, color: C.text2 }}
                  dangerouslySetInnerHTML={{ __html: row.n }}
                />
              </div>
              <div
                style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: TYPE_SCALE.body,
                  color: C.navy,
                  fontWeight: 600,
                }}
              >
                {row.v}
              </div>
            </div>
          ))}
        </div>
      </div>

      <SlideMeta index={index} total={total} />
    </SlideFrame>
  );
}

// --- 10: Spremno za pokretanje --------------------------------------

function ReadySlide({ index, total }) {
  const items = [
    ['Smart matching', 'kategorije i parafraze riješene'],
    ['Eval suite', '17/18 ciljano, log po pitanju'],
    ['Security review', 'prošao, nalazi zatvoreni'],
    ['VPS deploy', 'sve komponente lokalno'],
    ['Embed snippet', 'jedan red u <head>'],
    ['Produkcija', 'spremno za pokretanje'],
  ];

  return (
    <SlideFrame bg="#ffffff">
      <Eyebrow>09 · Status</Eyebrow>
      <div style={{ height: SPACING.titleGap }} />
      <Title>Spremno za pokretanje.</Title>

      <div style={{ height: 64 }} />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '0 80px',
          flex: 1,
          alignContent: 'center',
        }}
      >
        {items.map(([h, b], i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 28,
              padding: '24px 0',
              borderBottom: `1px solid ${C.borderSoft}`,
            }}
          >
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: 99,
                background: '#eafbef',
                color: C.green,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 22,
                flexShrink: 0,
              }}
            >
              ✓
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div
                style={{
                  fontSize: TYPE_SCALE.body,
                  fontWeight: 600,
                  color: C.navy,
                  letterSpacing: '-0.01em',
                }}
              >
                {h}
              </div>
              <div
                style={{ fontSize: TYPE_SCALE.small, color: C.text2 }}
                dangerouslySetInnerHTML={{ __html: b }}
              />
            </div>
          </div>
        ))}
      </div>

      <div style={{ height: 24 }} />

      <div
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: TYPE_SCALE.micro,
          color: C.text2,
        }}
      >
        Slijedeći korak: zeleno svjetlo — i krećemo.
      </div>

      <SlideMeta index={index} total={total} />
    </SlideFrame>
  );
}

// --- 11: Kontakt ----------------------------------------------------

function ContactSlide({ index, total }) {
  return (
    <SlideFrame bg={C.peach} padded={false}>
      <div
        style={{
          flex: 1,
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          alignItems: 'stretch',
        }}
      >
        <div
          style={{
            padding: `${SPACING.paddingTop}px ${SPACING.paddingX}px ${SPACING.paddingBottom}px`,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            gap: 40,
          }}
        >
          <Eyebrow>10 · Kontakt</Eyebrow>

          <Title size={120}>
            Hvala<span style={{ color: C.orange }}>.</span>
          </Title>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div style={{ fontSize: TYPE_SCALE.body, color: C.navy, fontWeight: 600 }}>
              BitLab d.o.o.
            </div>
            <div
              style={{
                fontSize: TYPE_SCALE.small,
                color: C.text,
                lineHeight: 1.55,
              }}
            >
              Jevrejska 37, 78000 Banja Luka<br />
              prodaja@bitlab.rs · 066 516 174<br />
              webshop.bitlab.rs
            </div>
            <div
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: TYPE_SCALE.micro,
                color: C.text2,
                marginTop: 8,
              }}
            >
              JIB: 4403711250001
            </div>
          </div>
        </div>

        {/* Right panel */}
        <div
          style={{
            background: '#ffe8db',
            position: 'relative',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            padding: `${SPACING.paddingTop}px ${SPACING.paddingX}px ${SPACING.paddingBottom}px`,
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: TYPE_SCALE.micro,
              color: C.navy,
              opacity: 0.7,
              letterSpacing: '0.18em',
              textTransform: 'uppercase',
            }}
          >
            Otvoreni za demo uživo
          </div>

          <div
            style={{
              fontSize: 100,
              fontWeight: 700,
              color: C.navy,
              letterSpacing: '-0.04em',
              lineHeight: 0.95,
            }}
          >
            Pričekamo<br />
            <span style={{ color: C.orange }}>zeleno</span><br />
            svjetlo.
          </div>

          <div
            style={{
              display: 'flex',
              gap: 28,
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: TYPE_SCALE.micro,
              color: C.navy,
              opacity: 0.7,
            }}
          >
            <span>● chat</span>
            <span>● voice</span>
            <span>● e-mail</span>
          </div>
        </div>
      </div>
    </SlideFrame>
  );
}

// --- Export to window -----------------------------------------------

Object.assign(window, {
  TYPE_SCALE,
  SPACING,
  C,
  CoverSlide,
  ContextSlide,
  ChannelsSlide,
  DemoSlide,
  DifferentiatorSlide,
  EvalSlide,
  StackSlide,
  SecuritySlide,
  CostSlide,
  ReadySlide,
  ContactSlide,
});

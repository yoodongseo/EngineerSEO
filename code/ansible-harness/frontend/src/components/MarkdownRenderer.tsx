"use client";

import {
  Children,
  isValidElement,
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ComponentPropsWithoutRef,
  type ReactElement,
  type ReactNode,
} from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

interface MarkdownRendererProps {
  content: string;
  streaming?: boolean;
  className?: string;
}

interface MarkdownCodeProps extends ComponentPropsWithoutRef<"code"> {
  inline?: boolean;
  children?: ReactNode;
}

interface MarkdownPreProps extends ComponentPropsWithoutRef<"pre"> {
  children?: ReactNode;
}

interface CodeElementProps extends ComponentPropsWithoutRef<"code"> {
  children?: ReactNode;
  className?: string;
}

interface MarkdownLinkProps extends ComponentPropsWithoutRef<"a"> {
  href?: string;
  children?: ReactNode;
}

function flattenText(children: ReactNode): string {
  return Children.toArray(children)
    .map((child) => {
      if (typeof child === "string" || typeof child === "number") {
        return String(child);
      }

      if (isValidElement<{ children?: ReactNode }>(child)) {
        return flattenText(child.props.children);
      }

      return "";
    })
    .join("");
}

function isCodeElement(child: ReactNode): child is ReactElement<CodeElementProps> {
  return isValidElement<CodeElementProps>(child) && child.type === "code";
}

function getCodeLanguage(className?: string): string | null {
  const languageMatch = className?.match(/language-([\w-]+)/i);
  return languageMatch?.[1] ?? null;
}

function normalizeStreamingMarkdown(content: string, streaming: boolean): string {
  if (!streaming) {
    return content;
  }

  const fenceMatches = content.match(/```/g);
  return fenceMatches && fenceMatches.length % 2 === 1
    ? [content, "", "```"].join("\n")
    : content;
}

function getSafeHref(href?: string): string | undefined {
  if (!href) {
    return undefined;
  }

  const safeHrefPattern = /^(https?:|mailto:|tel:|\/|#)/i;
  return safeHrefPattern.test(href) ? href : undefined;
}

function CodeBlock({
  code,
  language,
  codeProps,
}: {
  code: string;
  language: string | null;
  codeProps: CodeElementProps;
}) {
  const [copied, setCopied] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);

      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        setCopied(false);
        timeoutRef.current = null;
      }, 1800);
    } catch {
      setCopied(false);
    }
  }, [code]);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return (
    <div className="markdown-code-block">
      <div className="markdown-code-toolbar">
        <span className="markdown-code-language">{language ?? "text"}</span>
        <button
          type="button"
          className="markdown-code-copy"
          onClick={() => {
            void handleCopy();
          }}
          aria-label={copied ? "코드가 복사되었습니다" : "코드 복사"}
        >
          {copied ? "복사됨" : "복사"}
        </button>
      </div>
      <pre className="markdown-code-pre">
        <code {...codeProps}>
          {codeProps.children}
        </code>
      </pre>
    </div>
  );
}

function MarkdownCode({
  inline,
  children,
  ...props
}: MarkdownCodeProps) {
  if (inline) {
    return (
      <code className="markdown-inline-code" {...props}>
        {children}
      </code>
    );
  }

  return <code {...props}>{children}</code>;
}

function MarkdownPre({ children }: MarkdownPreProps) {
  const firstChild = Children.toArray(children)[0];

  if (!isCodeElement(firstChild)) {
    return <pre className="markdown-code-pre">{children}</pre>;
  }

  const code = flattenText(firstChild.props.children).replace(/\n$/, "");

  return (
    <CodeBlock
      code={code}
      language={getCodeLanguage(firstChild.props.className)}
      codeProps={firstChild.props}
    />
  );
}

function MarkdownLink({ href, children, ...props }: MarkdownLinkProps) {
  const safeHref = getSafeHref(href);

  if (!safeHref) {
    return <span className="markdown-link-disabled">{children}</span>;
  }

  const isExternal = /^https?:\/\//i.test(safeHref);

  return (
    <a
      href={safeHref}
      target={isExternal ? "_blank" : undefined}
      rel={isExternal ? "noopener noreferrer nofollow" : undefined}
      {...props}
    >
      {children}
    </a>
  );
}

function MarkdownRenderer({
  content,
  streaming = false,
  className,
}: MarkdownRendererProps) {
  const normalizedContent = useMemo(
    () => normalizeStreamingMarkdown(content, streaming),
    [content, streaming]
  );

  const rootClassName = ["markdown-renderer", className].filter(Boolean).join(" ");

  return (
    <div className={rootClassName}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeHighlight, { detect: false, ignoreMissing: true }]]}
        skipHtml
        components={{
          pre: MarkdownPre,
          code: MarkdownCode,
          a: MarkdownLink,
          table: ({ children }) => (
            <div className="markdown-table-wrap">
              <table className="markdown-table">{children}</table>
            </div>
          ),
          img: () => null,
        }}
      >
        {normalizedContent}
      </ReactMarkdown>
    </div>
  );
}

export default memo(MarkdownRenderer);

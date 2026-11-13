"use client";

import type { FormEvent, ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { buttonVariants } from "@/components/ui/button";
import {
  SORT_KEYS,
  SORT_LABELS,
  formActionHref,
  type PostingFilters,
  type SkillChoice,
} from "@/lib/catalog/filters";
import { SENIORITY_LABELS, SOURCE_META, WORKPLACE_LABELS } from "@/lib/catalog/labels";
import { SENIORITY_LEVELS, SOURCES, WORKPLACES } from "@/lib/catalog/types";
import { cn } from "cn";

const controlClass =
  "h-11 w-full rounded-lg border border-input bg-card px-3 text-sm text-foreground outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

function Field({
  id,
  label,
  children,
}: {
  id: string;
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      {children}
    </div>
  );
}

export function PostingFilters({
  filters,
  skills,
  dateMin,
  dateMax,
  rangeError,
}: {
  filters: PostingFilters;
  skills: SkillChoice[];
  dateMin: string | null;
  dateMax: string | null;
  rangeError: boolean;
}) {
  const router = useRouter();
  const selectedSkill =
    skills.find((choice) => choice.skill.toLowerCase() === filters.skill?.toLowerCase())?.skill ??
    filters.skill ??
    "";
  const skillOptions =
    filters.skill && selectedSkill === filters.skill && !skills.some((choice) => choice.skill === filters.skill)
      ? [{ skill: filters.skill, count: 0 }, ...skills]
      : skills;

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    router.push(formActionHref(new FormData(event.currentTarget)), { scroll: false });
  }

  return (
    <form method="get" action="/" autoComplete="off" onSubmit={onSubmit} className="flex flex-col gap-4">
      <fieldset className="flex flex-col gap-4">
        <legend className="sr-only">Filter postings</legend>
        <Field id="posting-q" label="Search">
          <input
            id="posting-q"
            name="q"
            type="search"
            defaultValue={filters.q}
            maxLength={200}
            placeholder="Title, company, skill, or location"
            className={controlClass}
          />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Field id="posting-seniority" label="Seniority">
            <select id="posting-seniority" name="seniority" defaultValue={filters.seniority ?? ""} className={controlClass}>
              <option value="">Any seniority</option>
              {SENIORITY_LEVELS.map((level) => (
                <option key={level} value={level}>
                  {SENIORITY_LABELS[level]}
                </option>
              ))}
            </select>
          </Field>
          <Field id="posting-workplace" label="Workplace">
            <select id="posting-workplace" name="workplace" defaultValue={filters.workplace ?? ""} className={controlClass}>
              <option value="">Any workplace</option>
              {WORKPLACES.map((place) => (
                <option key={place} value={place}>
                  {WORKPLACE_LABELS[place]}
                </option>
              ))}
            </select>
          </Field>
          <Field id="posting-skill" label="Skill">
            <select id="posting-skill" name="skill" defaultValue={selectedSkill} className={controlClass}>
              <option value="">Any skill</option>
              {skillOptions.map((choice) => (
                <option key={choice.skill} value={choice.skill}>
                  {choice.count > 0 ? `${choice.skill} (${choice.count})` : choice.skill}
                </option>
              ))}
            </select>
          </Field>
          <Field id="posting-source" label="Source">
            <select id="posting-source" name="source" defaultValue={filters.source ?? ""} className={controlClass}>
              <option value="">Any source</option>
              {SOURCES.map((source) => (
                <option key={source} value={source}>
                  {SOURCE_META[source].name}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="flex min-h-11 items-center gap-3 rounded-lg border border-input bg-card px-3 sm:col-span-2 lg:col-span-1">
            <input
              id="posting-junior"
              name="junior"
              type="checkbox"
              value="1"
              defaultChecked={filters.juniorOnly}
              className="size-4 accent-primary"
            />
            <span>
              <span className="block text-sm font-medium">Junior-friendly only</span>
              <span className="block text-xs text-muted-foreground">Intern and junior titles</span>
            </span>
          </label>
          <Field id="posting-from" label="First seen from">
            <input
              id="posting-from"
              name="from"
              type="date"
              defaultValue={filters.from ?? ""}
              min={dateMin ?? undefined}
              max={dateMax ?? undefined}
              aria-describedby={rangeError ? "date-range-error" : undefined}
              className={controlClass}
            />
          </Field>
          <Field id="posting-to" label="First seen to">
            <input
              id="posting-to"
              name="to"
              type="date"
              defaultValue={filters.to ?? ""}
              min={dateMin ?? undefined}
              max={dateMax ?? undefined}
              aria-describedby={rangeError ? "date-range-error" : undefined}
              className={controlClass}
            />
          </Field>
          <div className="grid grid-cols-2 gap-4 sm:col-span-2 lg:col-span-1">
            <Field id="posting-sort" label="Sort by">
              <select id="posting-sort" name="sort" defaultValue={filters.sort} className={controlClass}>
                {SORT_KEYS.map((key) => (
                  <option key={key} value={key}>
                    {SORT_LABELS[key]}
                  </option>
                ))}
              </select>
            </Field>
            <Field id="posting-dir" label="Order">
              <select id="posting-dir" name="dir" defaultValue={filters.dir} className={controlClass}>
                <option value="asc">Ascending</option>
                <option value="desc">Descending</option>
              </select>
            </Field>
          </div>
        </div>
      </fieldset>
      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" className={cn(buttonVariants({ className: "h-11 px-4" }))}>
          Apply filters
        </button>
        <Link href="/" scroll={false} className={cn(buttonVariants({ variant: "outline", className: "h-11 px-4" }))}>
          Clear
        </Link>
        <p className="text-sm text-muted-foreground">The address bar keeps this view, so it can be shared.</p>
      </div>
    </form>
  );
}

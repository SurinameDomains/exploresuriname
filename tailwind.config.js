/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./generate.py", "./oilgas_pages.py", "./market.py", "./business_pages.py", "./douane.py"],
  theme: { extend: {} },
  plugins: [],
  // Nav class compaction (Oct 2026): these utilities were only written out in
  // nav_html() and now live inside @apply in input.css. Safelisted so
  // tailwind.css never loses them.
  // bg-gray-200, px-1.5 and select-none were only written in the old World Cup
  // page builder (removed Oct 2026); kept so tailwind.css stays unchanged.
  safelist: ["left-1/2", "top-full", "min-w-[190px]", "duration-200",
             "bg-gray-200", "px-1.5", "select-none"],
}

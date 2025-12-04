import { Skeleton } from "@/components/ui/skeleton"

export default function SettingsLoading() {
  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar skeleton */}
      <div className="w-52 border-r border-border p-4 space-y-4">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-8 w-3/4" />
        <Skeleton className="h-8 w-3/4" />
        <Skeleton className="h-8 w-3/4" />
      </div>

      {/* Main content skeleton */}
      <div className="flex-1 flex flex-col items-center justify-start p-8">
        {/* Logo placeholder */}
        <Skeleton className="w-64 h-64 rounded-full mb-4" />
        
        {/* Title placeholder */}
        <Skeleton className="h-12 w-48 mb-2" />
        <Skeleton className="h-4 w-64 mb-8" />

        {/* Cards grid skeleton */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 max-w-5xl">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-36 w-full rounded-xl" />
          ))}
        </div>
      </div>
    </div>
  )
}

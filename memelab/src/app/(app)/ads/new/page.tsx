"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AdWizard } from "@/components/ads/wizard";

export default function NewAdPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/ads">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Novo Video Ad</h1>
          <p className="text-muted-foreground">
            Configure e crie um video ad para seu produto
          </p>
        </div>
      </div>

      <AdWizard />
    </div>
  );
}

import {
  Activity, Binary, Cable, Cpu, Database, FileStack, GitBranch, HardDrive, Layers, Lock, MemoryStick, Network, Server, Split, Zap,
  type LucideIcon,
} from "lucide-react";

export interface Topic { name: string; description: string; icon: LucideIcon }

/** Short UI descriptions only — learning content comes from the backend. */
export const TOPICS: Topic[] = [
  { name: "Processes", description: "Programs in execution, states and the PCB.", icon: Activity },
  { name: "Threads", description: "Lightweight units of execution within a process.", icon: GitBranch },
  { name: "System Calls", description: "The interface between programs and the kernel.", icon: Cable },
  { name: "CPU Scheduling", description: "How the OS chooses which process runs next.", icon: Cpu },
  { name: "Process Synchronization", description: "Coordinating access to shared data.", icon: Network },
  { name: "Semaphores", description: "Signalling primitives for mutual exclusion.", icon: Lock },
  { name: "Deadlocks", description: "Conditions, prevention, avoidance and detection.", icon: Zap },
  { name: "Memory Management", description: "Allocating and protecting main memory.", icon: MemoryStick },
  { name: "Paging", description: "Fixed-size pages, frames and page tables.", icon: Layers },
  { name: "Segmentation", description: "Logical, variable-size memory segments.", icon: Split },
  { name: "Virtual Memory", description: "Demand paging and page replacement.", icon: Database },
  { name: "TLB", description: "Caching address translations.", icon: Binary },
  { name: "Disk Scheduling", description: "Ordering disk I/O requests.", icon: HardDrive },
  { name: "File Systems", description: "Files, directories and allocation methods.", icon: FileStack },
  { name: "Virtualization", description: "Running multiple OS instances on shared hardware.", icon: Server },
];

from array import *

######################################################################

def int_to_8bytes(value):
    return array('B',[(value >> (8*i)) & 0xff for i in range(0,8)])
    
def int_from_8bytes(b):
    return sum( b[i] << (8*i) for i in range(0,8))

NULL = 0

######################################################################

# page table at each level fills exactly one frame

class PagingSimulation: # 9+9+9+9+12 bits per virtual address

    def __init__(self, ram_bytes, offsetbits):
        self.mem = array('B', [NULL] * ram_bytes)  # Simulates main memory
        self.CR3 = NULL
        self.freeframe = 0
        self.current_pid = None
        self.pagetables = dict()
        self.offsetbits = offsetbits
        self.pagesize = 2**self.offsetbits
        self.pagetable_bytes = 8 * 2**9
        self.maskoffset = 2**self.offsetbits - 1
        self.masklevel = 2**9 - 1
        self.tlb = {}  # Dictionary for TLB
        self.max_tlb_entries = 512  # Maximum TLB size
        self.tlb_order = []  # To track FIFO order for eviction
        self.context_switch(0)
        

    def read8bytes_from_memory(self, a): # read 64-bit integer from physical memory addresses a,a+1,a+2,a+3,a+4,a+5,a+6,a+7
        return int_from_8bytes( self.mem[a:a+8] )
    
    def write8bytes_to_memory(self, a, val): # writes 64-bit integer into physical memory addresses a,a+1,a+2,a+3,a+4,a+5,a+6,a+7
        self.mem[a:a+8] = int_to_8bytes(val)
    
    def context_switch(self, process_id):
        
        if self.current_pid == process_id:
            print("warning: already has pid {}", process_id)
            return
        
        if process_id not in self.pagetables:
            
            self.freeframe += 1
            A = self.freeframe*self.pagesize
            self.mem[A:A+self.pagetable_bytes] = array('B', [NULL] * self.pagetable_bytes) # add page table at highest level and 
            self.pagetables[process_id] = A
            
        self.current_pid = process_id
        self.CR3 = self.pagetables[self.current_pid] # set page table pointer in CR3 register 
    
    def tlb_lookup(self, pagenr):
        """Check if the page number is in the TLB and return the frame if found."""
        if (self.current_pid, pagenr) in self.tlb:
            return self.tlb[(self.current_pid, pagenr)]
        return NULL

    def tlb_insert(self, pagenr, frame):
        """Insert a new mapping into the TLB, evicting old entries if necessary."""
        if len(self.tlb) >= self.max_tlb_entries:
            oldest_entry = self.tlb_order.pop(0)  # FIFO eviction
            del self.tlb[oldest_entry]

        self.tlb[(self.current_pid, pagenr)] = frame
        self.tlb_order.append((self.current_pid, pagenr))

    def context_switch(self, process_id):
        """Switch to a new process and reset the page tables."""
        if self.current_pid == process_id:
            print("Warning: Already on PID", process_id)
            return

        if process_id not in self.pagetables:
            self.freeframe += 1
            A = self.freeframe * self.pagesize
            self.mem[A:A+self.pagetable_bytes] = array('B', [NULL] * self.pagetable_bytes)
            self.pagetables[process_id] = A

        self.current_pid = process_id
        self.CR3 = self.pagetables[self.current_pid]
        self.tlb.clear()  # Clear the TLB on context switch

    def translate_to_physicaladress(self, virtualaddress):
        """Translate a virtual address to a physical address with TLB support."""
        pagenr = virtualaddress >> self.offsetbits
        offset = virtualaddress & self.maskoffset

        # Step 1: Check TLB
        frame = self.tlb_lookup(pagenr)
        if frame != NULL:
            return frame * self.pagesize + offset

        # Step 2: Walk the page table if not in TLB
        i1 = (pagenr >> (9 * 3)) & self.masklevel
        i2 = (pagenr >> (9 * 2)) & self.masklevel
        i3 = (pagenr >> (9 * 1)) & self.masklevel
        i4 = (pagenr >> (9 * 0)) & self.masklevel

        A = self.CR3
        B = self.read8bytes_from_memory(A + i1 * 8)
        C = self.read8bytes_from_memory(B + i2 * 8)
        D = self.read8bytes_from_memory(C + i3 * 8)
        F = self.read8bytes_from_memory(D + i4 * 8)

        # Step 3: Update TLB
        self.tlb_insert(pagenr, F)

        return F * self.pagesize + offset
        
    def print_pagetable_sizes(self):
        
    
    def add_entry(self, pagenr):
        
        A = self.CR3
        
        if self.offsetbits == 12: # page number has then 36 bits with 9 bits per level (there are 4 levels in this case)
            
            i1 = (pagenr >> 9*3) & self.masklevel # most significant 9 bits of page nr
            i2 = (pagenr >> 9*2) & self.masklevel
            i3 = (pagenr >> 9*1) & self.masklevel
            i4 = (pagenr >> 9*0) & self.masklevel # least significant 9 bits of page nr
            
            B = self.read8bytes_from_memory(A+i1*8)
            
            if B == NULL: 
                
                self.freeframe += 1
                B = self.freeframe * self.pagesize
                self.mem[B:B+self.pagetable_bytes] = array('B', [NULL] * self.pagetable_bytes) # add page table below highest level
                self.write8bytes_to_memory(A+i1*8, B) # link it in entry at highest level
                
            
            C = self.read8bytes_from_memory(B+i2*8)
            
            if C == NULL: 
                
                self.freeframe += 1
                C = self.freeframe * self.pagesize
                self.mem[C:C+self.pagetable_bytes] = array('B', [NULL] * self.pagetable_bytes) # add page table above lowest level 
                self.write8bytes_to_memory(B+i2*8, C) # link it in entry below highest level
                
            D = self.read8bytes_from_memory(C+i3*8)
            
            if D == NULL: 
                
                self.freeframe += 1
                D = self.freeframe * self.pagesize
                self.mem[D:D+self.pagetable_bytes] = array('B', [NULL] * self.pagetable_bytes) # Add page table at lowest level and 
                self.write8bytes_to_memory(C+i3*8, D) # link it in entry above lowest level
                
            
            F = self.read8bytes_from_memory(D+i4*8)
            
            if F == NULL: 
                
                self.freeframe += 1
                F = self.freeframe * self.pagesize
                self.mem[F:F+self.pagesize] = array('B', [NULL] * self.pagetable_bytes) # add frame 
                self.write8bytes_to_memory(D+i4*8, F) # link it in entry at lowest level
                return F
        
            print("page not free!")
            return None
        
        if self.offsetbits == 21: # page number has then 27 bits with 9 bits per level (there are 3 levels in this case)
            
            pass # ADD CODE HERE FOR BONUS QUESTION 3c.i
            
        if self.offsetbits == 30: # page number has then 18 bits with 9 bits per level (there are 2 levels in this case)
            
            pass # ADD CODE HERE FOR BONUS QUESTION 3c.ii
        
    def translate_to_physicaladress(self, virtualaddress):
        
        pagenr = virtualaddress >> self.offsetbits # most significant bits of virtual address
        offset = virtualaddress & self.maskoffset # least significant bits of virtual address
        
        if self.offsetbits == 12:
        
            i1 = (pagenr >> 9*3) & self.masklevel # most significant 9 bits of page nr
            i2 = (pagenr >> 9*2) & self.masklevel
            i3 = (pagenr >> 9*1) & self.masklevel
            i4 = (pagenr >> 9*0) & self.masklevel # least significant 9 bits of page nr
                
            A = self.CR3
        
            # Note: self.read8bytes_from_memory(a) reads 64-bit value
            #       from bytes at physical memory addresses
            #       a,a+1,a+2,a+3,a+4,a+5,a+6,a+7
        
            B = self.read8bytes_from_memory(A+i1*8)
            C = self.read8bytes_from_memory(B+i2*8)
            D = self.read8bytes_from_memory(C+i3*8)
            F = self.read8bytes_from_memory(D+i4*8)
        
            return F*self.pagesize+offset
            
        if self.offsetbits == 21:
            
            pass # ADD CODE HERE FOR BONUS QUESTION 3c.i
            
        if self.offsetbits == 30:
            
            pass # ADD CODE HERE FOR BONUS QUESTION 3c.ii

    def write_8bytes_tovirtualmemory(self, virtualaddress, val):
        
        physicaladdress = self.translate_to_physicaladress(virtualaddress)        
        self.write8bytes_to_memory(physicaladdress, val)

    def print_memory_state(self): ## Using only One Level
        print("\n=== MEMORY STATE ===")
        print(f"Total frames used: {self.freeframe}")
        print(f"Total memory used by page tables: {self.freeframe * self.pagesize} bytes")

        print("\n=== Page Table Entries ===")
        for process_id, base_addr in self.pagetables.items():
            print(f"Process {process_id} -> Page Table at Physical Address: {base_addr:#x}")

        # Calculate memory usage if a single-level page table was used
        single_level_memory_usage = (2**36) * 8  # 36-bit page numbers, each entry is 8 bytes
        print(f"\nSingle-Level Page Table Size: {single_level_memory_usage / (1024**3):.2f} GB")

        
# MATCHES FIGURE 3 ON LAB SHEET
        
pt = PagingSimulation(ram_bytes=128*(1024**2), offsetbits=12) # 128 MB RAM

pt.context_switch(123) # switch to process with id 123
assert(16628512713 == ( (123 << 27) + (456 << 18) + (379 << 9)+ 457 ))
assert(68110388073237 == (16628512713 << 12) + 789)
assert(68110388073237 == 0x3df22f7c9315)

pt.add_entry( (1 << 27) + (2 << 18) + (3 << 9)+ 4 ) # related to question
pt.add_entry( (123 << 27) + (456 << 18) + (2 << 9)+ 457 ) # related to question
pt.add_entry( (123 << 27) + (456 << 18) + (379 << 9)+ 457 ) # related to question
pt.add_entry( (123 << 27) + (456 << 18) + (379 << 9)+ 500 ) # related to question

pt.write_8bytes_tovirtualmemory(0x3df22f7c9315, 51) # write 51 into virtual address 0x3df22f7c9315

pt.print_pagetable_size()


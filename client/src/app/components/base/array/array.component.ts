import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { ButtonComponent } from '../button/button.component';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { fadeInAnimation } from '../../../animations/shared.animations';

export type SortDirection = 'asc' | 'desc';

/**
 * Generic data table: pagination, a shallow global search, and column
 * sorting via consumer-supplied comparators. Rows/cells are still content-
 * projected by the caller (`<tr appLine>`/`<td appColumn>`), this component
 * only owns the chrome (toolbar, header, pagination) around them.
 *
 * To sort a column, pass a comparator keyed by its exact `columns_names`
 * label: `[sortableColumns]="{'Email': (a, b) => a.email.localeCompare(b.email)}"`.
 * Columns without an entry in `sortableColumns` aren't clickable.
 */
@Component({
  selector: 'app-array',
  standalone: true,
  imports: [CommonModule, FormsModule, ButtonComponent],
  templateUrl: './array.component.html',
  styleUrl: './array.component.scss',
  animations: [fadeInAnimation],
})
export class ArrayComponent implements OnChanges {
  @Input() columns_names: string[] = [];
  @Input() records: any[] = [];
  @Input() pageSize: number = 10;
  @Input() pageSizeOptions: number[] = [10, 20, 50];
  @Input() emptyMessage: string = 'No records found';
  @Input() sortableColumns: { [columnName: string]: (a: any, b: any) => number } = {};

  currentPage: number = 1;
  totalPages: number = 0;
  searchTerm: string = '';
  currentPageSize: number = 10;
  sortColumn: string | null = null;
  sortDirection: SortDirection = 'asc';

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['pageSize']?.firstChange) {
      this.currentPageSize = this.pageSize || 10;
    }
    if (changes['records']) {
      this.currentPage = 1;
    }
  }

  isSortable(columnName: string): boolean {
    return !!this.sortableColumns[columnName];
  }

  get filteredSortedRecords(): any[] {
    let result = this.records;

    const term = this.searchTerm.trim().toLowerCase();
    if (term) {
      result = result.filter((record) => this.matchesSearch(record, term));
    }

    if (this.sortColumn && this.sortableColumns[this.sortColumn]) {
      const compare = this.sortableColumns[this.sortColumn];
      const direction = this.sortDirection === 'asc' ? 1 : -1;
      result = [...result].sort((a, b) => compare(a, b) * direction);
    }

    return result;
  }

  private matchesSearch(record: any, term: string): boolean {
    return Object.values(record ?? {}).some((value) => {
      if (typeof value === 'string' || typeof value === 'number') {
        return String(value).toLowerCase().includes(term);
      }
      return false;
    });
  }

  get paginatedRecords() {
    const filtered = this.filteredSortedRecords;
    this.totalPages = Math.max(1, Math.ceil(filtered.length / this.currentPageSize));
    if (this.currentPage > this.totalPages) {
      this.currentPage = this.totalPages;
    }
    const startIndex = (this.currentPage - 1) * this.currentPageSize;
    return filtered.slice(startIndex, startIndex + this.currentPageSize);
  }

  onSearchChange(value: string): void {
    this.searchTerm = value;
    this.currentPage = 1;
  }

  onPageSizeChange(size: number): void {
    this.currentPageSize = Number(size);
    this.currentPage = 1;
  }

  onSortClick(columnName: string): void {
    if (!this.isSortable(columnName)) {
      return;
    }
    if (this.sortColumn === columnName) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortColumn = columnName;
      this.sortDirection = 'asc';
    }
    this.currentPage = 1;
  }

  nextPage() {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
    }
  }

  previousPage() {
    if (this.currentPage > 1) {
      this.currentPage--;
    }
  }
}
